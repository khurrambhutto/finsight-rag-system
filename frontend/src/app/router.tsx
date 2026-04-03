import { Navigate, createBrowserRouter } from 'react-router-dom'

import { AppShell } from '../components/app-shell'
import { SignInPage } from '../features/auth/sign-in-page'
import { ChatPage } from '../features/chat/chat-page'
import { SettingsPage } from '../features/settings/settings-page'
import { ProtectedRoute } from '../routes/protected-route'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/app/chat" replace />,
  },
  {
    path: '/sign-in/*',
    element: <SignInPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: '/app',
        element: <AppShell />,
        children: [
          {
            index: true,
            element: <Navigate to="/app/chat" replace />,
          },
          {
            path: 'chat',
            element: <ChatPage />,
          },
          {
            path: 'chat/:threadId',
            element: <ChatPage />,
          },
          {
            path: 'settings',
            element: <SettingsPage />,
          },
        ],
      },
    ],
  },
])
