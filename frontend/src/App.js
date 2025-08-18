import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Badge } from './components/ui/badge';
import { Avatar, AvatarFallback } from './components/ui/avatar';
import { ScrollArea } from './components/ui/scroll-area';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from './components/ui/sheet';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Textarea } from './components/ui/textarea';
import { toast } from 'sonner';
import { 
  Send, 
  Plus, 
  Hash, 
  Users, 
  MessageSquare, 
  Smile, 
  Paperclip, 
  Edit3, 
  Check, 
  X,
  Settings,
  LogOut,
  Menu
} from 'lucide-react';
import './App.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  // Auth state
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  const [registerForm, setRegisterForm] = useState({ username: '', email: '', password: '' });
  const [isLogin, setIsLogin] = useState(true);

  // App state
  const [channels, setChannels] = useState([]);
  const [users, setUsers] = useState([]);
  const [selectedChannel, setSelectedChannel] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [editingMessage, setEditingMessage] = useState(null);
  const [editContent, setEditContent] = useState('');
  const [ws, setWs] = useState(null);
  const [onlineUsers, setOnlineUsers] = useState(new Set());

  // UI state
  const [showNewChannelDialog, setShowNewChannelDialog] = useState(false);
  const [newChannelName, setNewChannelName] = useState('');
  const [newChannelDescription, setNewChannelDescription] = useState('');
  const [newChannelDomain, setNewChannelDomain] = useState('general');
  const [newChannelTTL, setNewChannelTTL] = useState(false);
  const [newChannelTTLSeconds, setNewChannelTTLSeconds] = useState(3600);
  const [showEmojiPicker, setShowEmojiPicker] = useState(null);
  const [uploading, setUploading] = useState(false);

  // Domain-specific state
  const [playerStats, setPlayerStats] = useState([]);
  const [gameSchedule, setGameSchedule] = useState([]);
  const [flashcards, setFlashcards] = useState([]);
  const [studyMaterials, setStudyMaterials] = useState([]);
  const [activeSprint, setActiveSprint] = useState(null);

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Popular emojis for quick access
  const popularEmojis = ['👍', '❤️', '😂', '😮', '😢', '😡', '👏', '🔥', '💯', '✅'];

  const domainTypes = [
    { value: 'general', label: 'General Chat', icon: '💬' },
    { value: 'sports', label: 'Sports Team', icon: '🏀' },
    { value: 'study', label: 'Study Group', icon: '📚' },
    { value: 'agile', label: 'Agile/DevOps', icon: '🚀' }
  ];

  const ttlOptions = [
    { value: 300, label: '5 minutes' },
    { value: 900, label: '15 minutes' },
    { value: 1800, label: '30 minutes' },
    { value: 3600, label: '1 hour' },
    { value: 21600, label: '6 hours' },
    { value: 86400, label: '24 hours' }
  ];

  // Configure axios defaults
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    }
  }, [token]);

  // Authentication
  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(`${API_URL}/api/auth/login`, loginForm);
      const { access_token, user: userData } = response.data;
      
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setUser(userData);
      toast.success(`Welcome back, ${userData.username}!`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(`${API_URL}/api/auth/register`, registerForm);
      const { access_token, user: userData } = response.data;
      
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setUser(userData);
      toast.success(`Welcome to SlackLite, ${userData.username}!`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Registration failed');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    if (ws) {
      ws.close();
    }
    toast.success('Logged out successfully');
  };

  // WebSocket connection
  useEffect(() => {
    if (token && user) {
      const wsUrl = `${API_URL.replace('http', 'ws')}/api/ws/${token}`;
      const websocket = new WebSocket(wsUrl);

      websocket.onopen = () => {
        console.log('WebSocket connected');
        setWs(websocket);
      };

      websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      };

      websocket.onclose = () => {
        console.log('WebSocket disconnected');
        setWs(null);
      };

      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      return () => {
        websocket.close();
      };
    }
  }, [token, user]);

  const handleWebSocketMessage = useCallback((data) => {
    switch (data.type) {
      case 'new_message':
        setMessages(prev => [...prev, data]);
        break;
      case 'message_edited':
        setMessages(prev => prev.map(msg => 
          msg.id === data.id ? data : msg
        ));
        break;
      case 'reaction_added':
        setMessages(prev => prev.map(msg => 
          msg.id === data.message_id ? { ...msg, reactions: data.reactions } : msg
        ));
        break;
      case 'message_expiring':
        // Show expiration warning
        toast.warning(`Message expiring in ${Math.round((new Date(data.expires_at) - new Date()) / 1000)} seconds`);
        break;
      case 'message_expired':
        // Remove expired message from UI
        setMessages(prev => prev.filter(msg => msg.id !== data.message_id));
        break;
      case 'user_status':
        setOnlineUsers(prev => {
          const newSet = new Set(prev);
          if (data.is_online) {
            newSet.add(data.user_id);
          } else {
            newSet.delete(data.user_id);
          }
          return newSet;
        });
        break;
      case 'channel_settings_updated':
        toast.success(`Channel settings updated by ${data.updated_by}`);
        loadChannels(); // Refresh channel data
        break;
      case 'player_stats_updated':
        toast.success(`Player stats updated for ${data.player_name}`);
        if (selectedChannel?.id === data.channel_id) {
          loadDomainData();
        }
        break;
      default:
        break;
    }
  }, [selectedChannel]);

  // Load initial data
  useEffect(() => {
    if (token) {
      loadChannels();
      loadUsers();
      getCurrentUser();
    }
  }, [token]);

  const getCurrentUser = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/auth/me`);
      setUser(response.data);
    } catch (error) {
      console.error('Failed to get current user:', error);
      handleLogout();
    }
  };

  const loadChannels = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/channels`);
      setChannels(response.data);
      if (response.data.length > 0 && !selectedChannel) {
        setSelectedChannel(response.data[0]);
      }
    } catch (error) {
      toast.error('Failed to load channels');
    }
  };

  const loadUsers = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/users`);
      setUsers(response.data);
    } catch (error) {
      toast.error('Failed to load users');
    }
  };

  // Load domain-specific data when channel changes
  const loadDomainData = useCallback(async () => {
    if (!selectedChannel) return;
    
    try {
      const domain = selectedChannel.domain_type;
      
      if (domain === 'sports') {
        const [statsResponse, scheduleResponse] = await Promise.all([
          axios.get(`${API_URL}/api/sports/stats/${selectedChannel.id}`),
          axios.get(`${API_URL}/api/sports/schedule/${selectedChannel.id}`)
        ]);
        setPlayerStats(statsResponse.data);
        setGameSchedule(scheduleResponse.data);
      } else if (domain === 'study') {
        const [flashcardsResponse, materialsResponse] = await Promise.all([
          axios.get(`${API_URL}/api/study/flashcards/${selectedChannel.id}`),
          axios.get(`${API_URL}/api/study/materials/${selectedChannel.id}`)
        ]);
        setFlashcards(flashcardsResponse.data);
        setStudyMaterials(materialsResponse.data);
      } else if (domain === 'agile') {
        const sprintResponse = await axios.get(`${API_URL}/api/agile/sprint/${selectedChannel.id}`);
        setActiveSprint(sprintResponse.data);
      }
    } catch (error) {
      console.error('Failed to load domain data:', error);
    }
  }, [selectedChannel]);

  // Load domain data when channel selection changes
  useEffect(() => {
    if (selectedChannel) {
      loadChannelMessages(selectedChannel.id);
      loadDomainData();
      setSelectedUser(null);
    }
  }, [selectedChannel, loadDomainData]);

  useEffect(() => {
    if (selectedUser) {
      loadDirectMessages(selectedUser.id);
      setSelectedChannel(null);
    }
  }, [selectedUser]);

  const loadChannelMessages = async (channelId) => {
    try {
      const response = await axios.get(`${API_URL}/api/messages/channel/${channelId}`);
      setMessages(response.data);
    } catch (error) {
      toast.error('Failed to load messages');
    }
  };

  const loadDirectMessages = async (userId) => {
    try {
      const response = await axios.get(`${API_URL}/api/messages/direct/${userId}`);
      setMessages(response.data);
    } catch (error) {
      toast.error('Failed to load messages');
    }
  };

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Channel management
  const handleCreateChannel = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/api/channels`, {
        name: newChannelName,
        description: newChannelDescription,
        is_public: true,
        ttl_enabled: newChannelTTL,
        ttl_seconds: newChannelTTLSeconds,
        domain_type: newChannelDomain,
        domain_config: {}
      });
      
      setNewChannelName('');
      setNewChannelDescription('');
      setNewChannelDomain('general');
      setNewChannelTTL(false);
      setNewChannelTTLSeconds(3600);
      setShowNewChannelDialog(false);
      loadChannels();
      
      const domainLabel = domainTypes.find(d => d.value === newChannelDomain)?.label || 'General';
      toast.success(`${domainLabel} channel created successfully!`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create channel');
    }
  };

  const handleJoinChannel = async (channelId) => {
    try {
      await axios.post(`${API_URL}/api/channels/${channelId}/join`);
      loadChannels();
      toast.success('Joined channel successfully!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to join channel');
    }
  };

  // Message handling
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim()) return;

    try {
      await axios.post(`${API_URL}/api/messages`, {
        content: newMessage,
        channel_id: selectedChannel?.id,
        recipient_id: selectedUser?.id
      });
      
      setNewMessage('');
    } catch (error) {
      toast.error('Failed to send message');
    }
  };

  const handleEditMessage = async (messageId) => {
    try {
      await axios.put(`${API_URL}/api/messages/${messageId}`, {
        content: editContent
      });
      
      setEditingMessage(null);
      setEditContent('');
      toast.success('Message updated!');
    } catch (error) {
      toast.error('Failed to edit message');
    }
  };

  const handleAddReaction = async (messageId, emoji) => {
    try {
      await axios.post(`${API_URL}/api/messages/${messageId}/reactions`, {
        emoji: emoji
      });
      setShowEmojiPicker(null);
    } catch (error) {
      toast.error('Failed to add reaction');
    }
  };

  // File upload
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const uploadResponse = await axios.post(`${API_URL}/api/upload`, formData);
      
      // Send file message
      await axios.post(`${API_URL}/api/messages`, {
        content: uploadResponse.data.file_type === 'image' ? 
          `📷 ${uploadResponse.data.file_name}` : 
          `📎 ${uploadResponse.data.file_name}`,
        channel_id: selectedChannel?.id,
        recipient_id: selectedUser?.id
      });

      toast.success('File uploaded successfully!');
    } catch (error) {
      toast.error('Failed to upload file');
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
  };

  // Auth UI
  if (!token || !user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-purple-900 flex items-center justify-center p-4">
        <Card className="w-full max-w-md shadow-2xl border-0 bg-white/95 backdrop-blur-sm">
          <CardHeader className="text-center pb-6">
            <div className="w-20 h-20 bg-gradient-to-r from-blue-600 to-purple-600 rounded-3xl mx-auto mb-6 flex items-center justify-center shadow-lg">
              <MessageSquare className="w-10 h-10 text-white" />
            </div>
            <CardTitle className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              SlackLite
            </CardTitle>
            <p className="text-gray-600 font-medium">Real-time messaging made simple</p>
          </CardHeader>
          <CardContent>
            <Tabs value={isLogin ? 'login' : 'register'} onValueChange={(v) => setIsLogin(v === 'login')}>
              <TabsList className="grid w-full grid-cols-2 mb-6 bg-gray-100">
                <TabsTrigger value="login" className="font-semibold">Login</TabsTrigger>
                <TabsTrigger value="register" className="font-semibold">Sign Up</TabsTrigger>
              </TabsList>
              
              <TabsContent value="login">
                <form onSubmit={handleLogin} className="space-y-5">
                  <Input
                    placeholder="Username"
                    value={loginForm.username}
                    onChange={(e) => setLoginForm({...loginForm, username: e.target.value})}
                    className="border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 h-12"
                    required
                  />
                  <Input
                    type="password"
                    placeholder="Password"
                    value={loginForm.password}
                    onChange={(e) => setLoginForm({...loginForm, password: e.target.value})}
                    className="border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 h-12"
                    required
                  />
                  <Button type="submit" className="w-full h-12 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold text-lg">
                    Sign In
                  </Button>
                </form>
              </TabsContent>
              
              <TabsContent value="register">
                <form onSubmit={handleRegister} className="space-y-5">
                  <Input
                    placeholder="Username"
                    value={registerForm.username}
                    onChange={(e) => setRegisterForm({...registerForm, username: e.target.value})}
                    className="border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 h-12"
                    required
                  />
                  <Input
                    type="email"
                    placeholder="Email"
                    value={registerForm.email}
                    onChange={(e) => setRegisterForm({...registerForm, email: e.target.value})}
                    className="border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 h-12"
                    required
                  />
                  <Input
                    type="password"
                    placeholder="Password"
                    value={registerForm.password}
                    onChange={(e) => setRegisterForm({...registerForm, password: e.target.value})}
                    className="border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 h-12"
                    required
                  />
                  <Button type="submit" className="w-full h-12 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold text-lg">
                    Create Account
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Main App UI
  return (
    <div className="h-screen flex bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Mobile Menu */}
      <Sheet>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="md:hidden fixed top-4 left-4 z-50 text-white hover:bg-white/10">
            <Menu className="w-5 h-5" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-80 p-0 bg-slate-800 border-slate-700">
          <div className="flex flex-col h-full">
            <SheetHeader className="p-6 border-b border-slate-700">
              <SheetTitle className="flex items-center gap-2 text-white">
                <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <MessageSquare className="w-5 h-5 text-white" />
                </div>
                SlackLite
              </SheetTitle>
            </SheetHeader>
            <div className="flex-1 overflow-hidden">
              {/* Mobile sidebar content */}
              <SidebarContent 
                channels={channels}
                users={users}
                selectedChannel={selectedChannel}
                selectedUser={selectedUser}
                onlineUsers={onlineUsers}
                user={user}
                onChannelSelect={setSelectedChannel}
                onUserSelect={setSelectedUser}
                onCreateChannel={() => setShowNewChannelDialog(true)}
                onJoinChannel={handleJoinChannel}
                onLogout={handleLogout}
              />
            </div>
          </div>
        </SheetContent>
      </Sheet>

      {/* Desktop Sidebar */}
      <div className="hidden md:flex w-80 bg-gradient-to-b from-slate-800 to-slate-900 border-r border-slate-700 flex-col shadow-2xl">
        <SidebarContent 
          channels={channels}
          users={users}
          selectedChannel={selectedChannel}
          selectedUser={selectedUser}
          onlineUsers={onlineUsers}
          user={user}
          onChannelSelect={setSelectedChannel}
          onUserSelect={setSelectedUser}
          onCreateChannel={() => setShowNewChannelDialog(true)}
          onJoinChannel={handleJoinChannel}
          onLogout={handleLogout}
        />
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-white">
        {/* Chat Header */}
        <div className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 shadow-sm">
          <div className="flex items-center gap-3">
            {selectedChannel && (
              <>
                <div className="w-6 h-6 bg-blue-100 rounded flex items-center justify-center">
                  <Hash className="w-4 h-4 text-blue-600" />
                </div>
                <h1 className="text-xl font-bold text-gray-900">{selectedChannel.name}</h1>
                <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-200">
                  {selectedChannel.members?.length || 0} members
                </Badge>
              </>
            )}
            {selectedUser && (
              <>
                <Avatar className="w-8 h-8 ring-2 ring-blue-200">
                  <AvatarFallback className="bg-gradient-to-r from-blue-500 to-purple-600 text-white font-bold">
                    {selectedUser.username[0].toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <h1 className="text-xl font-bold text-gray-900">{selectedUser.username}</h1>
                {onlineUsers.has(selectedUser.id) && 
                  <Badge className="bg-green-100 text-green-700 hover:bg-green-200">
                    <div className="w-2 h-2 bg-green-500 rounded-full mr-1"></div>
                    Online
                  </Badge>
                }
              </>
            )}
          </div>
        </div>

        {/* Messages */}
        <ScrollArea className="flex-1 p-6 bg-gray-50">
          <div className="space-y-4">
            {messages.map((message) => (
              <MessageItem
                key={message.id}
                message={message}
                currentUser={user}
                editingMessage={editingMessage}
                editContent={editContent}
                showEmojiPicker={showEmojiPicker}
                onStartEdit={(msg) => {
                  setEditingMessage(msg.id);
                  setEditContent(msg.content);
                }}
                onCancelEdit={() => {
                  setEditingMessage(null);
                  setEditContent('');
                }}
                onSaveEdit={handleEditMessage}
                onEditContentChange={setEditContent}
                onShowEmojiPicker={setShowEmojiPicker}
                onAddReaction={handleAddReaction}
                popularEmojis={popularEmojis}
                formatTimestamp={formatTimestamp}
              />
            ))}
          </div>
          <div ref={messagesEndRef} />
        </ScrollArea>

        {/* Message Input */}
        <div className="p-6 bg-white border-t border-gray-200">
          <form onSubmit={handleSendMessage} className="flex items-center gap-3">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="hover:bg-gray-100 text-gray-600"
            >
              <Paperclip className="w-5 h-5" />
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileUpload}
              className="hidden"
              accept="image/*,application/pdf,.doc,.docx,.txt"
            />
            <Input
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              placeholder={
                selectedChannel 
                  ? `Message #${selectedChannel.name}` 
                  : selectedUser 
                    ? `Message ${selectedUser.username}` 
                    : "Select a channel or user to start messaging"
              }
              className="flex-1 border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={!selectedChannel && !selectedUser}
            />
            <Button 
              type="submit" 
              disabled={!newMessage.trim() || (!selectedChannel && !selectedUser)}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6"
            >
              <Send className="w-4 h-4" />
            </Button>
          </form>
        </div>
      </div>

      {/* Create Channel Dialog */}
      <Dialog open={showNewChannelDialog} onOpenChange={setShowNewChannelDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Channel</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateChannel} className="space-y-4">
            <Input
              placeholder="Channel name"
              value={newChannelName}
              onChange={(e) => setNewChannelName(e.target.value)}
              required
            />
            <Textarea
              placeholder="Channel description (optional)"
              value={newChannelDescription}
              onChange={(e) => setNewChannelDescription(e.target.value)}
            />
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setShowNewChannelDialog(false)}>
                Cancel
              </Button>
              <Button type="submit">Create Channel</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Sidebar Component
function SidebarContent({ 
  channels, 
  users, 
  selectedChannel, 
  selectedUser, 
  onlineUsers, 
  user, 
  onChannelSelect, 
  onUserSelect, 
  onCreateChannel, 
  onJoinChannel, 
  onLogout 
}) {
  return (
    <>
      {/* User Profile */}
      <div className="p-6 border-b border-slate-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <Avatar className="w-12 h-12 ring-2 ring-blue-400 ring-offset-2 ring-offset-slate-800">
                <AvatarFallback className="bg-gradient-to-r from-blue-500 to-purple-600 text-white font-bold text-lg">
                  {user.username[0].toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-500 border-2 border-slate-800 rounded-full"></div>
            </div>
            <div>
              <p className="font-bold text-white text-lg">{user.username}</p>
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <p className="text-sm text-green-400 font-medium">Online</p>
              </div>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onLogout} className="text-gray-400 hover:text-white hover:bg-slate-700">
            <LogOut className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Channels */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-gray-300 uppercase tracking-wider flex items-center gap-2">
              <Hash className="w-4 h-4" />
              Channels
            </h3>
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={onCreateChannel}
              className="text-gray-400 hover:text-white hover:bg-slate-700 w-6 h-6"
            >
              <Plus className="w-4 h-4" />
            </Button>
          </div>
          
          <div className="space-y-1">
            {channels.map((channel) => (
              <div
                key={channel.id}
                onClick={() => onChannelSelect(channel)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-200 group ${
                  selectedChannel?.id === channel.id
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'hover:bg-slate-700 text-gray-300 hover:text-white'
                }`}
              >
                <div className={`w-5 h-5 rounded flex items-center justify-center ${
                  selectedChannel?.id === channel.id ? 'bg-blue-700' : 'bg-slate-600 group-hover:bg-slate-600'
                }`}>
                  <Hash className="w-3 h-3" />
                </div>
                <span className="text-sm font-medium flex-1">{channel.name}</span>
                {!channel.members?.includes(user.id) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      onJoinChannel(channel.id);
                    }}
                    className="text-xs px-2 py-1 h-6 bg-slate-600 hover:bg-slate-500 text-white ml-auto"
                  >
                    Join
                  </Button>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Direct Messages */}
        <div className="p-4 border-t border-slate-700">
          <h3 className="text-sm font-bold text-gray-300 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Users className="w-4 h-4" />
            Direct Messages
          </h3>
          
          <div className="space-y-1">
            {users.filter(u => u.id !== user.id).map((otherUser) => (
              <div
                key={otherUser.id}
                onClick={() => onUserSelect(otherUser)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-200 group ${
                  selectedUser?.id === otherUser.id
                    ? 'bg-purple-600 text-white shadow-lg'
                    : 'hover:bg-slate-700 text-gray-300 hover:text-white'
                }`}
              >
                <div className="relative">
                  <Avatar className="w-7 h-7 ring-1 ring-slate-600">
                    <AvatarFallback className={`text-xs font-bold ${
                      selectedUser?.id === otherUser.id 
                        ? 'bg-purple-700 text-white' 
                        : 'bg-gradient-to-r from-teal-500 to-cyan-600 text-white'
                    }`}>
                      {otherUser.username[0].toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  {onlineUsers.has(otherUser.id) && (
                    <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-500 border-2 border-slate-800 rounded-full"></div>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium block truncate">{otherUser.username}</span>
                  {onlineUsers.has(otherUser.id) ? (
                    <span className="text-xs text-green-400">Online</span>
                  ) : (
                    <span className="text-xs text-gray-500">Offline</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

// Message Component
function MessageItem({ 
  message, 
  currentUser, 
  editingMessage, 
  editContent, 
  showEmojiPicker,
  onStartEdit, 
  onCancelEdit, 
  onSaveEdit, 
  onEditContentChange,
  onShowEmojiPicker,
  onAddReaction,
  popularEmojis,
  formatTimestamp 
}) {
  const isOwn = message.sender_id === currentUser.id;
  const isEditing = editingMessage === message.id;

  return (
    <div className={`flex gap-4 group hover:bg-gray-50 p-3 rounded-lg transition-colors ${isOwn ? 'flex-row-reverse' : ''}`}>
      <Avatar className="w-10 h-10 flex-shrink-0 ring-2 ring-gray-100">
        <AvatarFallback className={`font-bold text-white ${
          isOwn 
            ? 'bg-gradient-to-r from-blue-600 to-blue-700' 
            : 'bg-gradient-to-r from-emerald-500 to-teal-600'
        }`}>
          {message.sender_username[0].toUpperCase()}
        </AvatarFallback>
      </Avatar>
      
      <div className={`flex-1 max-w-2xl ${isOwn ? 'text-right' : ''}`}>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm font-bold text-gray-900">{message.sender_username}</span>
          <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
            {formatTimestamp(message.created_at)}
          </span>
          {message.edited_at && (
            <span className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded-full font-medium">
              edited
            </span>
          )}
        </div>
        
        {isEditing ? (
          <div className="space-y-3">
            <Textarea
              value={editContent}
              onChange={(e) => onEditContentChange(e.target.value)}
              className="w-full border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <div className="flex gap-2">
              <Button size="sm" onClick={() => onSaveEdit(message.id)} className="bg-green-600 hover:bg-green-700">
                <Check className="w-3 h-3 mr-1" />
                Save
              </Button>
              <Button size="sm" variant="outline" onClick={onCancelEdit} className="border-gray-300 hover:bg-gray-50">
                <X className="w-3 h-3 mr-1" />
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <>
            <div className={`inline-block max-w-full px-4 py-3 rounded-2xl shadow-sm ${
              isOwn 
                ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white' 
                : 'bg-white border border-gray-200 text-gray-900'
            }`}>
              <p className="text-sm leading-relaxed">{message.content}</p>
            </div>
            
            {/* Reactions */}
            {message.reactions && Object.keys(message.reactions).length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {Object.entries(message.reactions).map(([emoji, userIds]) => (
                  <button
                    key={emoji}
                    onClick={() => onAddReaction(message.id, emoji)}
                    className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium transition-all shadow-sm ${
                      userIds.includes(currentUser.id)
                        ? 'bg-blue-100 text-blue-700 border border-blue-200 hover:bg-blue-200'
                        : 'bg-gray-100 hover:bg-gray-200 text-gray-700 border border-gray-200'
                    }`}
                  >
                    <span className="text-base">{emoji}</span>
                    <span className="font-bold">{userIds.length}</span>
                  </button>
                ))}
              </div>
            )}
            
            {/* Message Actions */}
            <div className={`flex items-center gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity ${
              isOwn ? 'justify-end' : ''
            }`}>
              <Button
                variant="ghost"
                size="icon"
                className="w-8 h-8 hover:bg-gray-200"
                onClick={() => onShowEmojiPicker(showEmojiPicker === message.id ? null : message.id)}
              >
                <Smile className="w-4 h-4 text-gray-500" />
              </Button>
              
              {isOwn && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="w-8 h-8 hover:bg-gray-200"
                  onClick={() => onStartEdit(message)}
                >
                  <Edit3 className="w-4 h-4 text-gray-500" />
                </Button>
              )}
            </div>
            
            {/* Emoji Picker */}
            {showEmojiPicker === message.id && (
              <div className="flex flex-wrap gap-2 mt-3 p-3 bg-white border border-gray-200 rounded-xl shadow-lg">
                {popularEmojis.map((emoji) => (
                  <button
                    key={emoji}
                    onClick={() => onAddReaction(message.id, emoji)}
                    className="w-10 h-10 flex items-center justify-center hover:bg-gray-100 rounded-lg transition-colors text-lg"
                  >
                    {emoji}
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default App;