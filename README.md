# SlackLite - Real-time Messaging System

A modern, real-time messaging application built with FastAPI, React, and MongoDB. Features WebSocket-based messaging, channel management, direct messaging, file uploads, emoji reactions, and message editing.

## Features

### Core Messaging
- **Real-time messaging** with WebSocket connections
- **Channel-based communication** (public channels)
- **Direct 1:1 messaging** between users
- **Message persistence** with MongoDB
- **Message history** and pagination support
- **User presence tracking** (online/offline status)

### Advanced Features  
- **Message editing** with edit indicators
- **Emoji reactions** on messages with popular emoji picker
- **File uploads** (images, documents, PDFs)
- **Message threading** and reply system
- **User authentication** with JWT tokens
- **Mobile-responsive design** with modern UI

### Technical Features
- **WebSocket connection management** for real-time updates
- **JWT-based authentication** with secure token handling
- **MongoDB integration** with efficient message storage
- **File upload system** with static file serving
- **CORS configuration** for cross-origin requests
- **Error handling** and validation

## Getting Started

### Prerequisites
- **Node.js** 18+ and **Yarn**
- **Python** 3.8+ and **pip**
- **MongoDB** instance (local or cloud)

### Installation

1. **Clone and setup the project:**
```bash
git clone <repository-url>
cd slacklite
```

2. **Backend setup:**
```bash
cd backend
pip install -r requirements.txt

# Create .env file
echo "MONGO_URL=mongodb://localhost:27017" > .env
echo "JWT_SECRET=your-secret-key-here" >> .env
```

3. **Frontend setup:**
```bash
cd frontend
yarn install

# Create .env file
echo "REACT_APP_BACKEND_URL=http://localhost:8001" > .env
```

### Running the Application

1. **Start MongoDB:**
```bash
# If using local MongoDB
mongod
```

2. **Start the backend server:**
```bash
cd backend
python server.py
# Server runs on http://localhost:8001
```

3. **Start the frontend:**
```bash
cd frontend
yarn start
# App runs on http://localhost:3000
```

4. **Open your browser and navigate to `http://localhost:3000`**

## Architecture

### Backend (FastAPI)
```
/app/backend/
├── server.py              # Main FastAPI application
├── requirements.txt       # Python dependencies
└── .env                  # Environment variables
```

**Key Components:**
- **WebSocket Manager**: Handles real-time connections and message broadcasting
- **Authentication System**: JWT-based user registration and login
- **Message API**: CRUD operations for messages with reactions and editing
- **Channel Management**: Create, join, and manage public channels
- **File Upload Service**: Handle file uploads with proper mime-type detection

### Frontend (React)
```
/app/frontend/
├── src/
│   ├── App.js            # Main React component
│   ├── App.css           # Custom styles and animations
│   ├── components/ui/    # Shadcn/ui components
│   └── index.js          # Entry point
├── package.json          # Node.js dependencies
└── public/               # Static assets
```

**Key Features:**
- **Component Architecture**: Modular React components with hooks
- **Real-time UI Updates**: WebSocket integration for live messaging
- **Modern UI/UX**: Shadcn/ui components with Tailwind CSS
- **Responsive Design**: Mobile-first design with responsive layouts
- **State Management**: React hooks for efficient state handling

### Database Schema (MongoDB)

#### Users Collection
```javascript
{
  id: String,              // UUID
  username: String,        // Unique username
  email: String,          // User email
  password_hash: String,   // Bcrypt hashed password
  is_online: Boolean,     // Online status
  avatar_url: String,     // Profile picture URL
  created_at: DateTime    // Account creation timestamp
}
```

#### Channels Collection
```javascript
{
  id: String,              // UUID
  name: String,           // Channel name (unique)
  description: String,    // Channel description
  created_by: String,     // Creator user ID
  members: [String],      // Array of member user IDs
  is_public: Boolean,     // Public/private channel
  created_at: DateTime    // Channel creation timestamp
}
```

#### Messages Collection
```javascript
{
  id: String,              // UUID
  content: String,        // Message text content
  sender_id: String,      // Sender user ID
  sender_username: String, // Sender username (denormalized)
  channel_id: String,     // Target channel ID (for channel messages)
  recipient_id: String,   // Target user ID (for direct messages)
  message_type: String,   // "text", "file", "image"
  file_url: String,       // File URL for file messages
  file_name: String,      // Original filename
  reactions: {            // Emoji reactions
    "👍": [String],       // Array of user IDs who reacted
    "❤️": [String]
  },
  edited_at: DateTime,    // Last edit timestamp
  created_at: DateTime    // Message creation timestamp
}
```

## Usage Guide

### Getting Started
1. **Create an account** or **login** with existing credentials
2. **Join existing channels** or **create new ones**
3. **Start messaging** in channels or direct message other users

### Channel Management
- **Create Channel**: Click the "+" button next to "Channels" in the sidebar
- **Join Channel**: Click "Join" button on any public channel you're not a member of
- **View Members**: Channel member count is displayed in the header

### Messaging Features
- **Send Messages**: Type in the message input and press Enter or click Send
- **Edit Messages**: Click the edit icon on your own messages
- **Add Reactions**: Click the smile icon and select an emoji
- **Upload Files**: Click the paperclip icon to upload images or documents

### Direct Messaging
- **Start DM**: Click on any user in the "Direct Messages" section
- **Online Status**: Green dot indicates online users
- **Message History**: Scroll up to load previous messages

## API Reference

### Authentication Endpoints
```
POST /api/auth/register    # Create new user account
POST /api/auth/login       # Authenticate existing user
GET  /api/auth/me         # Get current user profile
```

### Channel Endpoints
```
GET  /api/channels                    # List all accessible channels
POST /api/channels                    # Create new channel
POST /api/channels/{id}/join          # Join a public channel
POST /api/channels/{id}/leave         # Leave a channel
```

### Message Endpoints
```
GET  /api/messages/channel/{id}       # Get channel message history
GET  /api/messages/direct/{user_id}   # Get direct message history
POST /api/messages                    # Send new message
PUT  /api/messages/{id}              # Edit existing message
POST /api/messages/{id}/reactions     # Add emoji reaction
```

### File Upload
```
POST /api/upload                      # Upload file (returns file URL)
```

### WebSocket Connection
```
WebSocket: /api/ws/{jwt_token}        # Real-time message connection
```

## Security Features

### Authentication & Authorization
- **JWT Token Authentication**: Secure token-based authentication
- **Password Hashing**: Bcrypt for secure password storage
- **Token Expiration**: 24-hour token expiration with refresh capability
- **Protected Routes**: API endpoints require valid authentication

### Data Validation
- **Input Sanitization**: Pydantic models for request validation
- **File Type Validation**: Restricted file upload types
- **CORS Configuration**: Proper cross-origin request handling

### WebSocket Security
- **Token-based WS Auth**: WebSocket connections require valid JWT
- **Connection Management**: Automatic cleanup of disconnected users
- **Message Broadcasting**: Secure message delivery to authorized recipients

## UI/UX Features

### Modern Design System
- **Shadcn/ui Components**: Professional, accessible UI components
- **Tailwind CSS**: Utility-first CSS framework for consistent styling
- **Inter Font**: Modern, readable typography
- **Responsive Design**: Mobile-first approach with breakpoint optimization

### Interactive Elements
- **Hover Effects**: Smooth transitions and hover states
- **Loading States**: Visual feedback for async operations
- **Animations**: Subtle animations for better user experience
- **Accessibility**: Keyboard navigation and screen reader support

### Real-time Visual Feedback
- **Online Indicators**: Real-time user presence with pulse animation
- **Message Status**: Delivery confirmation and edit indicators
- **Typing Indicators**: Show when users are composing messages
- **Notification System**: Toast notifications for important events

## 📱 Mobile Experience

### Responsive Design
- **Mobile-first Layout**: Optimized for touch interfaces
- **Slide-out Sidebar**: Space-efficient navigation on mobile
- **Touch-friendly Controls**: Larger touch targets for mobile users
- **Adaptive Typography**: Readable text sizes across devices

### Progressive Web App Features
- **Offline Support**: Basic offline functionality (planned)
- **Push Notifications**: Real-time message notifications (planned)
- **App-like Experience**: Full-screen mobile web app experience

## Performance Optimizations

### Frontend Performance
- **Component Memoization**: React.memo for expensive components
- **Lazy Loading**: Code splitting for reduced initial bundle size
- **Efficient Re-renders**: Optimized state updates and subscriptions
- **Virtual Scrolling**: Planned for large message histories

### Backend Performance
- **WebSocket Pooling**: Efficient connection management
- **Database Indexing**: Optimized MongoDB queries
- **Async Operations**: Non-blocking I/O operations
- **Connection Pooling**: MongoDB connection optimization

### Caching Strategy
- **Browser Caching**: Static asset caching
- **API Response Caching**: Planned Redis integration
- **WebSocket Message Buffering**: Efficient message delivery

## Development

### Code Style & Standards
- **ESLint Configuration**: Consistent JavaScript/React code style
- **Black Formatting**: Python code formatting
- **TypeScript Support**: Planned migration to TypeScript
- **Git Hooks**: Pre-commit hooks for code quality

### Testing Strategy
- **Unit Tests**: Component and utility function tests
- **Integration Tests**: API endpoint testing
- **E2E Tests**: Full user journey testing
- **WebSocket Testing**: Real-time feature testing

### Deployment Options

#### Development Environment
```bash
# Using supervisor (recommended for development)
sudo supervisorctl restart all
```

#### Production Deployment
```bash
# Docker deployment
docker-compose up -d

# Kubernetes deployment
kubectl apply -f k8s/
```

## Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and test thoroughly
4. Commit with descriptive messages: `git commit -m 'Add amazing feature'`
5. Push to your branch: `git push origin feature/amazing-feature`
6. Open a Pull Request with detailed description

### Bug Reports
- Use the GitHub issue tracker
- Include steps to reproduce
- Provide system information and error logs
- Add screenshots for UI issues

## 📋 Roadmap

### Phase 1 - Core Features ✅
- [x] Real-time messaging with WebSockets
- [x] User authentication and registration
- [x] Channel creation and management
- [x] Direct messaging
- [x] Message editing and reactions
- [x] File upload support

### Phase 2 - Enhanced Features 🚧
- [ ] Private channels with invitations
- [ ] Message search functionality
- [ ] User roles and permissions
- [ ] Message threads and replies
- [ ] Voice/video calling integration
- [ ] Push notifications

### Phase 3 - Scalability 📋
- [ ] Redis pub-sub for message broadcasting
- [ ] Database sharding for message storage
- [ ] CDN integration for file uploads
- [ ] Load balancing and horizontal scaling
- [ ] Performance monitoring and analytics

### Phase 4 - Advanced Features 📋
- [ ] Screen sharing and collaboration tools
- [ ] Bot integration and webhooks
- [ ] Message scheduling
- [ ] File collaboration and version control
- [ ] Advanced search with filters
- [ ] Custom emoji and themes

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ for real-time communication**

For questions, bug reports, or feature requests, please open an issue on GitHub or contact the development team.
