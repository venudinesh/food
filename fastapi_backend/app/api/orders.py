"""
Orders API router
"""
from typing import Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from app.core.database import get_db
from app.api.auth import get_current_active_user
from app.models.user import User
from app.models.order import (
    Order, OrderCreate, OrderUpdate, OrderSummary, OrderItem,
    OrderStatus, PaymentStatus, OrderTrackingInfo, OrderStats,
    OrderSearchRequest, OrderStatusUpdate, CookingSession, DeliveryPartner
)
from app.models.food import FoodItem, Restaurant

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=Order)
async def create_order(
    order_data: OrderCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create a new order"""
    # Validate restaurant exists and is open
    restaurant = db.query(Restaurant).filter(Restaurant.id == order_data.restaurant_id).first()
    if not restaurant or not restaurant.is_open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Restaurant not found or currently closed"
        )

    # Validate food items and calculate totals
    subtotal = 0.0
    order_items = []

    for item_data in order_data.items:
        food_item = db.query(FoodItem).filter(FoodItem.id == item_data.food_item_id).first()
        if not food_item or not food_item.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Food item {item_data.food_item_id} not found or unavailable"
            )

        # Calculate item total with customizations
        item_total = food_item.price * item_data.quantity

        # Add customization price modifiers
        for customization in item_data.customizations:
            # In a real implementation, you'd validate and calculate customization prices
            pass

        subtotal += item_total

        # Create order item
        order_item = OrderItem(
            food_item_id=item_data.food_item_id,
            name=food_item.name,
            description=food_item.description,
            image_url=food_item.image_url,
            quantity=item_data.quantity,
            unit_price=food_item.price,
            total_price=item_total,
            customizations=item_data.customizations,
            special_instructions=item_data.special_instructions
        )
        order_items.append(order_item)

    # Calculate totals
    tax_amount = subtotal * 0.08  # 8% tax
    delivery_fee = restaurant.delivery_fee
    discount_amount = 0.0  # Would calculate based on coupons
    total_amount = subtotal + tax_amount + delivery_fee - discount_amount

    # Generate order number
    order_number = f"ORD{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{current_user.id[:6].upper()}"

    # Create order
    order = Order(
        user_id=current_user.id,
        restaurant_id=order_data.restaurant_id,
        order_number=order_number,
        status=OrderStatus.PLACED,
        status_history=[{
            "status": OrderStatus.PLACED,
            "timestamp": datetime.utcnow().isoformat(),
            "notes": "Order placed successfully"
        }],
        subtotal=subtotal,
        tax_amount=tax_amount,
        delivery_fee=delivery_fee,
        discount_amount=discount_amount,
        total_amount=total_amount,
        payment_method=order_data.payment_method,
        payment_status=PaymentStatus.PENDING,
        delivery_address=order_data.delivery_address,
        delivery_instructions=order_data.delivery_instructions,
        special_requests=order_data.special_requests,
        coupon_code=order_data.coupon_code,
        placed_at=datetime.utcnow()
    )

    db.add(order)
    db.flush()  # Get order ID

    # Add order items
    for item in order_items:
        item.order_id = order.id
        db.add(item)

    db.commit()
    db.refresh(order)

    # Add background task for order processing
    background_tasks.add_task(process_order_creation, order.id, db)

    return order

async def process_order_creation(order_id: str, db: Session):
    """Background task to process order creation"""
    # This would typically:
    # 1. Send notifications to restaurant
    # 2. Process payment
    # 3. Assign delivery partner
    # 4. Update order status
    pass

@router.get("/", response_model=List[OrderSummary])
async def get_user_orders(
    status: Optional[OrderStatus] = None,
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get user's orders with optional filtering"""
    query = db.query(Order).filter(Order.user_id == current_user.id)

    if status:
        query = query.filter(Order.status == status)

    orders = (
        query.order_by(Order.placed_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    # Convert to summaries
    summaries = []
    for order in orders:
        restaurant = db.query(Restaurant).filter(Restaurant.id == order.restaurant_id).first()
        items_count = db.query(OrderItem).filter(OrderItem.order_id == order.id).count()

        summaries.append(OrderSummary(
            id=order.id,
            order_number=order.order_number,
            restaurant_name=restaurant.name if restaurant else "Unknown",
            status=order.status,
            total_amount=order.total_amount,
            placed_at=order.placed_at,
            estimated_delivery_time=order.estimated_delivery_time,
            items_count=items_count
        ))

    return summaries

@router.get("/{order_id}", response_model=Order)
async def get_order_details(
    order_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get detailed order information"""
    order = (
        db.query(Order)
        .options(
            joinedload(Order.items),
            joinedload(Order.cooking_session),
            joinedload(Order.delivery_partner)
        )
        .filter(
            Order.id == order_id,
            Order.user_id == current_user.id
        )
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return order

@router.get("/{order_id}/tracking", response_model=OrderTrackingInfo)
async def get_order_tracking(
    order_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get real-time order tracking information"""
    order = (
        db.query(Order)
        .options(
            joinedload(Order.delivery_partner),
            joinedload(Order.cooking_session)
        )
        .filter(
            Order.id == order_id,
            Order.user_id == current_user.id
        )
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return OrderTrackingInfo(
        order_id=order.id,
        current_status=order.status,
        status_history=order.status_history,
        estimated_delivery_time=order.estimated_delivery_time,
        delivery_partner=order.delivery_partner,
        cooking_session=order.cooking_session
    )

@router.put("/{order_id}/status", response_model=Order)
async def update_order_status(
    order_id: str,
    status_update: OrderStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update order status (for users to cancel orders)"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Only allow cancellation for certain statuses
    if status_update.status == OrderStatus.CANCELLED:
        if order.status in [OrderStatus.DELIVERED, OrderStatus.OUT_FOR_DELIVERY]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel order at this stage"
            )

        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.utcnow()
        order.status_history.append({
            "status": OrderStatus.CANCELLED,
            "timestamp": datetime.utcnow().isoformat(),
            "notes": status_update.notes or "Cancelled by user"
        })

        # Update payment status if needed
        if order.payment_status == PaymentStatus.COMPLETED:
            order.payment_status = PaymentStatus.REFUNDED

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status update"
        )

    db.commit()
    db.refresh(order)
    return order

@router.put("/{order_id}", response_model=Order)
async def update_order(
    order_id: str,
    order_update: OrderUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update order details (limited fields)"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Only allow updates for certain statuses and fields
    if order.status not in [OrderStatus.PLACED, OrderStatus.CONFIRMED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order cannot be modified at this stage"
        )

    # Update allowed fields
    update_data = order_update.dict(exclude_unset=True)
    allowed_fields = ["delivery_instructions", "special_requests"]

    for field in update_data:
        if field in allowed_fields:
            setattr(order, field, update_data[field])

    db.commit()
    db.refresh(order)
    return order

@router.get("/stats/user", response_model=OrderStats)
async def get_user_order_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get user's order statistics"""
    orders = db.query(Order).filter(Order.user_id == current_user.id).all()

    total_orders = len(orders)
    pending_orders = len([o for o in orders if o.status in [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.COOKING, OrderStatus.READY, OrderStatus.OUT_FOR_DELIVERY]])
    completed_orders = len([o for o in orders if o.status == OrderStatus.DELIVERED])
    cancelled_orders = len([o for o in orders if o.status == OrderStatus.CANCELLED])

    total_revenue = sum(o.total_amount for o in orders if o.status == OrderStatus.DELIVERED)
    completed_order_amounts = [o.total_amount for o in orders if o.status == OrderStatus.DELIVERED]
    average_order_value = sum(completed_order_amounts) / len(completed_order_amounts) if completed_order_amounts else 0

    return OrderStats(
        total_orders=total_orders,
        pending_orders=pending_orders,
        completed_orders=completed_orders,
        cancelled_orders=cancelled_orders,
        total_revenue=total_revenue,
        average_order_value=average_order_value
    )

# Cooking Session Endpoints

@router.get("/{order_id}/cooking-session", response_model=CookingSession)
async def get_cooking_session(
    order_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get cooking session for an order"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if not order.cooking_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No cooking session available for this order"
        )

    return order.cooking_session

@router.post("/{order_id}/cooking-session/start")
async def start_cooking_session(
    order_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Start cooking session for an order (typically called by restaurant)"""
    # In a real implementation, this would be called by the restaurant system
    # For demo purposes, allowing users to start their own sessions
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.status != OrderStatus.COOKING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be in cooking status to start live session"
        )

    if order.cooking_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cooking session already exists"
        )

    # Create cooking session
    cooking_session = CookingSession(
        order_id=order.id,
        chef_id="chef_demo_001",  # Would be actual chef ID
        title=f"Live Cooking: {order.order_number}",
        description="Watch your food being prepared live!",
        status="live",
        stream_url="https://example.com/live-stream",  # Would be actual stream URL
        is_live=True,
        actual_start_time=datetime.utcnow(),
        estimated_duration=30
    )

    db.add(cooking_session)
    db.commit()
    db.refresh(cooking_session)

    return {"message": "Cooking session started", "session": cooking_session}

# Admin/Restaurant endpoints (would require different authentication)

@router.get("/restaurant/{restaurant_id}", response_model=List[OrderSummary])
async def get_restaurant_orders(
    restaurant_id: str,
    status: Optional[OrderStatus] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
) -> Any:
    """Get orders for a restaurant (admin/restaurant endpoint)"""
    query = db.query(Order).filter(Order.restaurant_id == restaurant_id)

    if status:
        query = query.filter(Order.status == status)

    if date_from:
        query = query.filter(Order.placed_at >= date_from)

    if date_to:
        query = query.filter(Order.placed_at <= date_to)

    orders = (
        query.order_by(Order.placed_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    # Convert to summaries
    summaries = []
    for order in orders:
        user = db.query(User).filter(User.id == order.user_id).first()
        items_count = db.query(OrderItem).filter(OrderItem.order_id == order.id).count()

        summaries.append(OrderSummary(
            id=order.id,
            order_number=order.order_number,
            restaurant_name="",  # Already known
            status=order.status,
            total_amount=order.total_amount,
            placed_at=order.placed_at,
            estimated_delivery_time=order.estimated_delivery_time,
            items_count=items_count
        ))

    return summaries

@router.put("/restaurant/{order_id}/status", response_model=Order)
async def update_order_status_restaurant(
    order_id: str,
    status_update: OrderStatusUpdate,
    db: Session = Depends(get_db)
) -> Any:
    """Update order status by restaurant (admin endpoint)"""
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Update status with timestamp
    old_status = order.status
    order.status = status_update.status

    # Set appropriate timestamps
    now = datetime.utcnow()
    if status_update.status == OrderStatus.CONFIRMED:
        order.confirmed_at = now
    elif status_update.status == OrderStatus.PREPARING:
        order.preparing_at = now
    elif status_update.status == OrderStatus.COOKING:
        order.cooking_at = now
    elif status_update.status == OrderStatus.READY:
        order.ready_at = now
    elif status_update.status == OrderStatus.OUT_FOR_DELIVERY:
        order.out_for_delivery_at = now
    elif status_update.status == OrderStatus.DELIVERED:
        order.delivered_at = now
        order.actual_delivery_time = now

    # Add to status history
    order.status_history.append({
        "status": status_update.status,
        "timestamp": now.isoformat(),
        "notes": status_update.notes or f"Status changed from {old_status} to {status_update.status}"
    })

    db.commit()
    db.refresh(order)
    return order