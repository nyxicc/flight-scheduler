import pandas as pd
from datetime import datetime, timedelta
from collections import deque

class NotificationSystem:
    def __init__(self):
        self.pending_notifications = deque()
        self.notification_history = []
        self.notification_id_counter = 0
        
    def create_notification(self, notification_type, data):
        """
        Create a new notification
        Args:
            notification_type: 'team_join', 'team_leave', 'team_replacement', 'remainder_employee'
            data: dict with notification details
        """
        notification_id = self.notification_id_counter
        self.notification_id_counter += 1
        
        notification = {
            'id': notification_id,
            'type': notification_type,
            'timestamp': datetime.now(),
            'status': 'pending',
            'data': data
        }
        
        self.pending_notifications.append(notification)
        return notification_id
    
    def get_pending_notifications(self):
        """Get all pending notifications"""
        return list(self.pending_notifications)
    
    def approve_notification(self, notification_id, manual_override=None):
        """
        Approve a notification
        Args:
            notification_id: ID of notification to approve
            manual_override: Optional dict with manual changes (e.g., different team assignment)
        """
        # Find notification
        notification = None
        for notif in self.pending_notifications:
            if notif['id'] == notification_id:
                notification = notif
                break
        
        if not notification:
            return False, "Notification not found"
        
        # Update status
        notification['status'] = 'approved'
        notification['approved_at'] = datetime.now()
        notification['manual_override'] = manual_override
        
        # Move to history
        self.pending_notifications.remove(notification)
        self.notification_history.append(notification)
        
        return True, notification
    
    def reject_notification(self, notification_id, reason=None):
        """Reject a notification"""
        notification = None
        for notif in self.pending_notifications:
            if notif['id'] == notification_id:
                notification = notif
                break
        
        if not notification:
            return False, "Notification not found"
        
        notification['status'] = 'rejected'
        notification['rejected_at'] = datetime.now()
        notification['rejection_reason'] = reason
        
        self.pending_notifications.remove(notification)
        self.notification_history.append(notification)
        
        return True, notification
    
    def format_notification(self, notification):
        """Format notification for display"""
        notif_type = notification['type']
        data = notification['data']
        timestamp = notification['timestamp'].strftime('%H:%M:%S')
        
        if notif_type == 'team_join':
            return {
                'id': notification['id'],
                'time': timestamp,
                'title': f"Team Member Joining",
                'message': f"{data['employee_name']} is joining Team {data['team_name']}",
                'details': {
                    'Employee': data['employee_name'],
                    'Team': data['team_name'],
                    'Shift': f"{data['shift_start']} - {data['shift_end']}",
                    'Hours': data.get('total_hours', 'N/A')
                },
                'requires_action': True
            }
        
        elif notif_type == 'team_replacement':
            return {
                'id': notification['id'],
                'time': timestamp,
                'title': f"Team Member Replacement",
                'message': f"{data['joining_name']} will replace {data['leaving_name']} on Team {data['team_name']} at {data['replacement_time']}",
                'details': {
                    'Team': data['team_name'],
                    'Leaving': data['leaving_name'],
                    'Leaving At': data['replacement_time'],
                    'Joining': data['joining_name'],
                    'Joined At': data['join_time'],
                    'New Member Shift': f"{data['joining_shift_start']} - {data['joining_shift_end']}"
                },
                'requires_action': True
            }
        
        elif notif_type == 'team_leave':
            return {
                'id': notification['id'],
                'time': timestamp,
                'title': f"Team Member Leaving",
                'message': f"{data['employee_name']} is leaving Team {data['team_name']} (no replacement available)",
                'details': {
                    'Employee': data['employee_name'],
                    'Team': data['team_name'],
                    'Leaving At': data['leave_time'],
                    'Team Size After': data['remaining_team_size']
                },
                'requires_action': True
            }
        
        elif notif_type == 'remainder_employee':
            return {
                'id': notification['id'],
                'time': timestamp,
                'title': f"Unassigned Employee Needs Team",
                'message': f"{data['employee_name']} needs to be assigned to a team",
                'details': {
                    'Employee': data['employee_name'],
                    'Shift': f"{data['shift_start']} - {data['shift_end']}",
                    'Hours': data.get('total_hours', 'N/A'),
                    'Suggested Team': data.get('suggested_team', 'None')
                },
                'requires_action': True,
                'allow_manual_selection': True
            }
        
        return None
    
    def get_notification_count(self):
        """Get count of pending notifications"""
        return len(self.pending_notifications)
    
    def clear_old_notifications(self, hours=24):
        """Clear notification history older than specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        self.notification_history = [
            n for n in self.notification_history 
            if n['timestamp'] > cutoff_time
        ]

if __name__ == "__main__":
    print("NotificationSystem class ready!")
    print("Manages team change notifications and approvals")