# Text-to-SQL Frontend

A Next.js chat interface for interacting with the Text-to-SQL AI agent.

## Features

- Natural language queries to SQL conversion
- Real-time streaming responses via SSE
- Syntax-highlighted SQL display
- Query results in a responsive table
- Session management for conversation continuity
- Dark mode support

## Prerequisites

- Node.js 18+
- Backend running on `http://localhost:8000`

## Getting Started

1. Install dependencies:

```bash
npm install
```

2. Start the development server:

```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Environment

The frontend proxies API requests to `http://localhost:8000`. To change this, edit `next.config.mjs`.

## Project Structure

```
src/
├── app/
│   ├── layout.tsx        # Root layout
│   ├── page.tsx          # Home (redirects to /chat)
│   ├── globals.css       # Global styles
│   └── chat/
│       └── page.tsx      # Chat page
├── components/
│   └── chat/
│       ├── ChatContainer.tsx      # Main chat wrapper
│       ├── ChatInput.tsx          # Input form
│       ├── MessageBubble.tsx      # Message display
│       ├── MessageList.tsx        # Message list
│       ├── ResultsTable.tsx       # Query results table
│       ├── SQLDisplay.tsx         # SQL code display
│       └── StreamingIndicator.tsx # Loading indicator
├── hooks/
│   └── useChat.ts        # Chat state management
├── lib/
│   └── api/
│       ├── client.ts     # API client with SSE
│       └── types.ts      # TypeScript types
└── types/
    └── chat.ts           # Chat-specific types
```

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
