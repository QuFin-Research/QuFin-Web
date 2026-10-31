import { create } from 'zustand';
// import { persist } from 'zustand/middleware';
import type { NotificationStatus, NotificationAction } from '@/components/ui/notification-card';

export type Notification = {
  id: string;
  title: string;
  body: string;
  status: NotificationStatus;
  createdAt: string;
  actions?: NotificationAction[];
};

type NotificationState = {
  notifications: Notification[];
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  removeNotification: (id: string) => void;
  addNotification: (notification: Omit<Notification, 'status'>) => void;
  unreadCount: () => number;
};

const minutesAgo = (m: number) => new Date(Date.now() - 1000 * 60 * m).toISOString();

const mockNotifications: Notification[] = [
  {
    id: '1',
    title: 'XAUUSD signal turned bullish',
    body: 'Gold moved to a high-conviction bullish 5-day outlook after the latest close.',
    status: 'unread',
    createdAt: minutesAgo(5),
    actions: [{ id: 'open-xauusd', label: 'Open XAUUSD', type: 'redirect', style: 'primary' }]
  },
  {
    id: '2',
    title: 'US CPI release at 13:30 GMT',
    body: 'High-impact release. Expect wider spreads on USD pairs and gold around the print.',
    status: 'unread',
    createdAt: minutesAgo(45),
    actions: [{ id: 'open-overview', label: 'View scorecard', type: 'redirect', style: 'primary' }]
  },
  {
    id: '3',
    title: 'CFTC positioning updated',
    body: 'Weekly Commitments of Traders data is in. Positioning drivers have been refreshed.',
    status: 'unread',
    createdAt: minutesAgo(60 * 3),
    actions: [{ id: 'open-markets', label: 'View markets', type: 'redirect', style: 'primary' }]
  },
  {
    id: '4',
    title: 'Decision review due',
    body: 'One of your journal decisions has reached its maximum holding period.',
    status: 'read',
    createdAt: minutesAgo(60 * 24),
    actions: [{ id: 'open-journal', label: 'Open journal', type: 'redirect', style: 'primary' }]
  }
];

export const useNotificationStore = create<NotificationState>()(
  // To enable persistence across refreshes, uncomment the persist wrapper below:
  // persist(
  (set, get) => ({
    notifications: mockNotifications,

    markAsRead: (id) =>
      set((state) => ({
        notifications: state.notifications.map((n) =>
          n.id === id ? { ...n, status: 'read' as const } : n
        )
      })),

    markAllAsRead: () =>
      set((state) => ({
        notifications: state.notifications.map((n) => ({
          ...n,
          status: 'read' as const
        }))
      })),

    removeNotification: (id) =>
      set((state) => ({
        notifications: state.notifications.filter((n) => n.id !== id)
      })),

    addNotification: (notification) =>
      set((state) => ({
        notifications: [{ ...notification, status: 'unread' as const }, ...state.notifications]
      })),

    unreadCount: () => get().notifications.filter((n) => n.status === 'unread').length
  })
  //   ,
  //   { name: 'notifications' }
  // )
);
