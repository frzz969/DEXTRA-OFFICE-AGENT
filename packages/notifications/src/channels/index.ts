/**
 * Notification channel contracts.
 */

export type NotificationChannel = 'in_app' | 'email' | 'webhook';

export type NotificationType = 'approval' | 'system' | 'agent' | 'alert';

export interface NotificationMessage {
  id: string;
  type: NotificationType;
  title: string;
  body: string;
  /** Optional workspace view to deep-link to. */
  linkView?: string;
  createdAt: string;
}

export interface NotificationTransport {
  readonly channel: NotificationChannel;
  send(message: NotificationMessage): Promise<void>;
}

export interface EmailMessage extends NotificationMessage {
  to: string;
  subject?: string;
}

export interface InAppMessage extends NotificationMessage {
  userId: string;
}
