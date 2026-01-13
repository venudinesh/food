'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '@/lib/auth-context';
import { useRouter } from 'next/navigation';
import { io, Socket } from 'socket.io-client';

interface StreamRoom {
  room_id: string;
  order_id: number;
  chef_id: number;
  customer_id: number;
  status: string;
  participants: Array<{
    user_id: number;
    user_type: string;
    joined_at: string;
    socket_id?: string;
  }>;
  created_at: string;
  stream_type: string;
  quality: string;
}

export default function StreamPage({ params }: { params: { roomId: string } }) {
  const { user, isAuthenticated } = useAuth();
  const router = useRouter();
  const [streamInfo, setStreamInfo] = useState<StreamRoom | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [participants, setParticipants] = useState<Array<{user_id: number, user_type: string}>>([]);
  const [messages, setMessages] = useState<Array<{message: string, sender_id: number, timestamp: string}>>([]);

  const socketRef = useRef<Socket | null>(null);
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);

  const roomId = params.roomId;

  const fetchStreamInfo = useCallback(async () => {
    try {
      const response = await fetch(`http://localhost:5000/api/streams/${roomId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setStreamInfo(data.stream);
      } else {
        setError('Stream not found or access denied');
      }
    } catch {
      setError('Failed to load stream information');
    } finally {
      setIsLoading(false);
    }
  }, [roomId]);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    fetchStreamInfo();
  }, [isAuthenticated, roomId, fetchStreamInfo, router]);

  const initializeWebRTC = useCallback(async () => {
    try {
      const configuration = {
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' },
          { urls: 'stun:stun1.l.google.com:19302' }
        ]
      };

      const peerConnection = new RTCPeerConnection(configuration);
      peerConnectionRef.current = peerConnection;

      // Get user media
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true
      });

      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
      }

      // Add tracks to peer connection
      stream.getTracks().forEach(track => {
        peerConnection.addTrack(track, stream);
      });

      // Handle remote stream
      peerConnection.ontrack = (event) => {
        if (remoteVideoRef.current && event.streams[0]) {
          remoteVideoRef.current.srcObject = event.streams[0];
        }
      };

      // Handle ICE candidates
      peerConnection.onicecandidate = (event) => {
        if (event.candidate && socketRef.current) {
          socketRef.current.emit('webrtc_ice_candidate', {
            room_id: roomId,
            candidate: event.candidate,
            from: user?.id
          });
        }
      };

      // Create offer if we're the chef (initiator)
      if (streamInfo?.chef_id === user?.id) {
        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);

        socketRef.current?.emit('webrtc_offer', {
          room_id: roomId,
          offer: offer,
          from: user?.id
        });
      }

    } catch (err) {
      console.error('Error initializing WebRTC:', err);
      setError('Failed to access camera/microphone');
    }
  }, [roomId, user?.id, streamInfo?.chef_id]);

  const handleOffer = useCallback(async (offer: RTCSessionDescriptionInit) => {
    if (!peerConnectionRef.current) return;

    try {
      await peerConnectionRef.current.setRemoteDescription(new RTCSessionDescription(offer));
      const answer = await peerConnectionRef.current.createAnswer();
      await peerConnectionRef.current.setLocalDescription(answer);

      socketRef.current?.emit('webrtc_answer', {
        room_id: roomId,
        answer: answer,
        from: user?.id
      });
    } catch (err) {
      console.error('Error handling offer:', err);
    }
  }, [roomId, user?.id]);

  const initializeSocket = useCallback(() => {
    if (!user || !streamInfo) return;

    const socket = io('http://localhost:8000');
    socketRef.current = socket;

    socket.on('connect', () => {
      setIsConnected(true);

      // Join the stream room
      const userType = streamInfo.chef_id === user.id ? 'chef' : 'customer';
      socket.emit('join_stream', {
        room_id: roomId,
        user_id: user.id,
        user_type: userType
      });
    });

    socket.on('stream_joined', (data) => {
      setStreamInfo(data.stream_info);
      initializeWebRTC();
    });

    socket.on('participant_joined', (data) => {
      setParticipants(prev => [...prev, { user_id: data.user_id, user_type: data.user_type }]);
    });

    socket.on('participant_left', (data) => {
      setParticipants(prev => prev.filter(p => p.user_id !== data.user_id));
    });

    socket.on('webrtc_offer', async (data) => {
      await handleOffer(data.offer);
    });

    socket.on('webrtc_answer', async (data) => {
      await handleAnswer(data.answer);
    });

    socket.on('webrtc_ice_candidate', async (data) => {
      await handleIceCandidate(data.candidate);
    });

    socket.on('stream_message', (data) => {
      setMessages(prev => [...prev, data]);
    });

    socket.on('stream_error', (data) => {
      setError(data.error);
    });
  }, [user, streamInfo, roomId, handleOffer, initializeWebRTC]);

  useEffect(() => {
    if (streamInfo && user) {
      initializeSocket();
      return () => {
        if (socketRef.current) {
          socketRef.current.disconnect();
        }
        if (peerConnectionRef.current) {
          peerConnectionRef.current.close();
        }
      };
    }
  }, [streamInfo, user, initializeSocket]);

  const handleAnswer = async (answer: RTCSessionDescriptionInit) => {
    if (!peerConnectionRef.current) return;

    try {
      await peerConnectionRef.current.setRemoteDescription(new RTCSessionDescription(answer));
    } catch (err) {
      console.error('Error handling answer:', err);
    }
  };

  const handleIceCandidate = async (candidate: RTCIceCandidateInit) => {
    if (!peerConnectionRef.current) return;

    try {
      await peerConnectionRef.current.addIceCandidate(new RTCIceCandidate(candidate));
    } catch (err) {
      console.error('Error handling ICE candidate:', err);
    }
  };

  const sendMessage = (message: string) => {
    if (socketRef.current && message.trim()) {
      socketRef.current.emit('stream_message', {
        room_id: roomId,
        message: message.trim(),
        sender_id: user?.id
      });
    }
  };

  const leaveStream = () => {
    if (socketRef.current) {
      socketRef.current.emit('leave_stream', {
        room_id: roomId,
        user_id: user?.id
      });
    }
    router.push('/profile');
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white p-8 rounded-lg shadow-lg max-w-md w-full">
          <div className="text-red-500 text-center mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-center mb-4">Stream Error</h2>
          <p className="text-gray-600 text-center mb-6">{error}</p>
          <button
            onClick={() => router.push('/profile')}
            className="w-full bg-orange-500 text-white py-2 px-4 rounded-lg font-semibold hover:bg-orange-600"
          >
            Back to Profile
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <div className="bg-gray-800 p-4 flex justify-between items-center">
        <div>
          <h1 className="text-xl font-semibold">Live Stream - Order #{streamInfo?.order_id}</h1>
          <div className="flex items-center space-x-4 text-sm text-gray-300">
            <span className={`px-2 py-1 rounded ${isConnected ? 'bg-green-600' : 'bg-red-600'}`}>
              {isConnected ? '🟢 Connected' : '🔴 Connecting...'}
            </span>
            <span>👥 {participants.length + 1} participants</span>
          </div>
        </div>
        <button
          onClick={leaveStream}
          className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg font-semibold"
        >
          Leave Stream
        </button>
      </div>

      <div className="flex h-[calc(100vh-80px)]">
        {/* Video Area */}
        <div className="flex-1 p-4">
          <div className="grid grid-cols-2 gap-4 h-full">
            {/* Local Video */}
            <div className="bg-gray-800 rounded-lg overflow-hidden">
              <video
                ref={localVideoRef}
                autoPlay
                muted
                playsInline
                className="w-full h-full object-cover"
              />
              <div className="absolute bottom-2 left-2 bg-black bg-opacity-50 px-2 py-1 rounded text-sm">
                You ({streamInfo?.chef_id === user?.id ? 'Chef' : 'Customer'})
              </div>
            </div>

            {/* Remote Video */}
            <div className="bg-gray-800 rounded-lg overflow-hidden relative">
              <video
                ref={remoteVideoRef}
                autoPlay
                playsInline
                className="w-full h-full object-cover"
              />
              <div className="absolute bottom-2 left-2 bg-black bg-opacity-50 px-2 py-1 rounded text-sm">
                {participants.length > 0 ? `${participants[0].user_type === 'chef' ? 'Chef' : 'Customer'}` : 'Waiting...'}
              </div>
            </div>
          </div>
        </div>

        {/* Chat Sidebar */}
        <div className="w-80 bg-gray-800 border-l border-gray-700 flex flex-col">
          <div className="p-4 border-b border-gray-700">
            <h3 className="font-semibold">Live Chat</h3>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((msg, index) => (
              <div key={index} className="bg-gray-700 rounded-lg p-3">
                <div className="text-sm text-gray-300">
                  {msg.sender_id === user?.id ? 'You' : 'Other'} • {new Date(msg.timestamp).toLocaleTimeString()}
                </div>
                <div className="text-white">{msg.message}</div>
              </div>
            ))}
          </div>

          {/* Message Input */}
          <div className="p-4 border-t border-gray-700">
            <div className="flex space-x-2">
              <input
                type="text"
                placeholder="Type a message..."
                className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400 focus:outline-none focus:border-orange-500"
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    sendMessage(e.currentTarget.value);
                    e.currentTarget.value = '';
                  }
                }}
              />
              <button
                onClick={(e) => {
                  const input = e.currentTarget.previousElementSibling as HTMLInputElement;
                  sendMessage(input.value);
                  input.value = '';
                }}
                className="bg-orange-600 hover:bg-orange-700 px-4 py-2 rounded-lg font-semibold"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}