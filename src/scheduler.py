import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from team_manager import TeamManager
from notification_system import NotificationSystem

class TeamBasedScheduler:
    def __init__(self, employee_handler, flight_handler):
        self.employee_handler = employee_handler
        self.flight_handler = flight_handler
        self.notification_system = NotificationSystem()
        self.team_manager = TeamManager(self.notification_system)
        self.assignments = []
        self.unassigned_flights = []
        
    def initialize_shift(self, shift_start_time):
        """
        Initialize teams at shift start
        Args:
            shift_start_time: datetime object (e.g., 2025-09-13 04:00:00)
        """
        teams, remainder = self.team_manager.form_initial_teams(
            self.employee_handler.employees_df,
            shift_start_time
        )
        
        if teams is None:
            return False, "Failed to form teams"
        
        print(f"✅ Formed {len(teams)} teams at shift start")
        for team_name, team_data in teams.items():
            print(f"   Team {team_name}: {len(team_data['members'])} members - {', '.join(team_data['member_names'])}")
        
        if remainder:
            print(f"\n⚠️  {len(remainder)} remainder employees need assignment:")
            for emp in remainder:
                print(f"   - {emp['employee_name']}")
        
        return True, remainder
    
    def assign_flights_in_window(self, current_time, window_hours=4):
        """
        Assign teams to flights within the time window
        Args:
            current_time: Current time
            window_hours: Look ahead window (default 4 hours)
        """
        window_end = current_time + timedelta(hours=window_hours)
        
        # Get flights in the window that aren't assigned yet
        upcoming_flights = self.flight_handler.flights_df[
            (self.flight_handler.flights_df['eta_datetime'] >= current_time) &
            (self.flight_handler.flights_df['eta_datetime'] <= window_end)
        ].copy()
        
        # Filter out already assigned flights
        assigned_flight_ids = [a['flight_id'] for a in self.assignments if a.get('team_assigned')]
        upcoming_flights = upcoming_flights[~upcoming_flights['flight_number'].isin(assigned_flight_ids)]
        
        # Sort by ETA
        upcoming_flights = upcoming_flights.sort_values('eta_datetime')
        
        print(f"\n📋 Assigning {len(upcoming_flights)} flights in {window_hours}-hour window")
        print(f"   Window: {current_time.strftime('%H:%M')} to {window_end.strftime('%H:%M')}")
        
        for _, flight in upcoming_flights.iterrows():
            self._assign_team_to_flight(flight)
        
        return len(upcoming_flights)
    
    def _assign_team_to_flight(self, flight):
        """Assign the best available team to a flight"""
        flight_id = flight['flight_number']
        eta = flight['eta_datetime']
        etd = flight['etd_datetime']
        heaviness = flight.get('heaviness', 'Medium')
        
        # Determine required team size
        required_size = 4 if heaviness == 'Medium' else 3  # Medium=4, Light=3
        
        # Get available teams
        available_teams = self.team_manager.get_available_teams(eta)
        
        if not available_teams:
            print(f"   ❌ Flight {flight_id} ({eta.strftime('%H:%M')}) - No teams available")
            self.unassigned_flights.append(flight_id)
            self._record_assignment(flight, None, False, "No teams available")
            return False
        
        # Filter teams by size requirement
        suitable_teams = [t for t in available_teams if t['size'] >= required_size]
        
        # If no suitable teams, use any available team
        if not suitable_teams:
            suitable_teams = available_teams
        
        # Select team with lowest flight count (fairness)
        suitable_teams.sort(key=lambda x: x['flight_count'])
        selected_team = suitable_teams[0]
        
        # Assign team to flight
        self.team_manager.assign_team_to_flight(selected_team['name'], flight)
        
        # Record assignment
        self._record_assignment(flight, selected_team, True, None)
        
        print(f"   ✅ Flight {flight_id} ({eta.strftime('%H:%M')}) → Team {selected_team['name']} (Count: {selected_team['flight_count']})")
        
        # Mark flight as complete when ETD passes
        self.team_manager.complete_flight(selected_team['name'], etd)
        
        return True
    
    def _record_assignment(self, flight, team, success, failure_reason=None):
        """Record a flight assignment"""
        assignment = {
            'flight_id': flight['flight_number'],
            'inbound_city': flight.get('city', 'Unknown'),
            'outbound_city': flight.get('outbound_city', 'Unknown'),
            'aircraft': flight.get('aircraft', 'Unknown'),
            'flight_route': f"{flight.get('city', 'Unknown')} → {flight.get('outbound_city', 'Unknown')}",
            'eta': flight['eta_datetime'],
            'etd': flight['etd_datetime'],
            'gate': flight.get('gate', 'Unknown'),
            'heaviness': flight.get('heaviness', 'Medium'),
            'turnaround_minutes': flight.get('turnaround_minutes', 0),
            'team_assigned': team['name'] if team else None,
            'team_members': team['members'] if team else [],
            'assignment_success': success,
            'failure_reason': failure_reason
        }
        
        self.assignments.append(assignment)
    
    def check_for_team_changes(self, current_time):
        """
        Check for team membership changes and create notifications
        This should be called periodically (every 5-10 minutes) during operations
        """
        notification_ids = self.team_manager.detect_and_notify_changes(
            self.employee_handler.employees_df,
            current_time
        )
        
        if notification_ids:
            print(f"\n🔔 {len(notification_ids)} new notification(s) created")
            
        return notification_ids
    
    def get_pending_notifications(self):
        """Get all pending notifications for display"""
        return self.notification_system.get_pending_notifications()
    
    def approve_team_change(self, notification_id, manual_team_assignment=None):
        """
        Approve a team change notification
        Args:
            notification_id: ID of notification to approve
            manual_team_assignment: Optional - manually specify which team for 'team_join' notifications
        """
        success, notification = self.notification_system.approve_notification(
            notification_id,
            manual_override={'team': manual_team_assignment} if manual_team_assignment else None
        )
        
        if not success:
            return False, "Notification not found"
        
        # Apply the change to teams
        notif_type = notification['type']
        data = notification['data']
        
        if notif_type == 'team_replacement':
            # Remove leaving member, add joining member
            team_name = data['team_name']
            leaving_id = data['leaving_id']
            joining_employee = self.employee_handler.employees_df[
                self.employee_handler.employees_df['employee_id'] == data['joining_id']
            ].iloc[0].to_dict()
            
            # Remove leaving member
            self.team_manager.teams[team_name]['members'] = [
                m for m in self.team_manager.teams[team_name]['members']
                if m['employee_id'] != leaving_id
            ]
            
            # Add joining member
            self.team_manager.teams[team_name]['members'].append(joining_employee)
            self.team_manager.teams[team_name]['member_ids'] = [m['employee_id'] for m in self.team_manager.teams[team_name]['members']]
            self.team_manager.teams[team_name]['member_names'] = [m['employee_name'] for m in self.team_manager.teams[team_name]['members']]
            
            print(f"✅ Approved: {data['joining_name']} replaced {data['leaving_name']} on Team {team_name}")
            
        elif notif_type == 'team_leave':
            # Just remove the leaving member
            team_name = data['team_name']
            employee_id = data['employee_id']
            
            self.team_manager.teams[team_name]['members'] = [
                m for m in self.team_manager.teams[team_name]['members']
                if m['employee_id'] != employee_id
            ]
            self.team_manager.teams[team_name]['member_ids'] = [m['employee_id'] for m in self.team_manager.teams[team_name]['members']]
            self.team_manager.teams[team_name]['member_names'] = [m['employee_name'] for m in self.team_manager.teams[team_name]['members']]
            self.team_manager.teams[team_name]['size'] = len(self.team_manager.teams[team_name]['members'])
            
            print(f"✅ Approved: {data['employee_name']} left Team {team_name}")
            
        elif notif_type == 'team_join':
            # Add person to team
            target_team = manual_team_assignment if manual_team_assignment else data.get('suggested_team')
            
            if not target_team or target_team == 'TBD':
                return False, "No team specified for new employee"
            
            joining_employee = self.employee_handler.employees_df[
                self.employee_handler.employees_df['employee_id'] == data['employee_id']
            ].iloc[0].to_dict()
            
            self.team_manager.teams[target_team]['members'].append(joining_employee)
            self.team_manager.teams[target_team]['member_ids'].append(data['employee_id'])
            self.team_manager.teams[target_team]['member_names'].append(data['employee_name'])
            self.team_manager.teams[target_team]['size'] = len(self.team_manager.teams[target_team]['members'])
            
            print(f"✅ Approved: {data['employee_name']} joined Team {target_team}")
        
        return True, "Change applied successfully"
        """Get summary of all assignments"""
        summary = {
            'total_flights': len(self.assignments),
            'assigned_flights': len([a for a in self.assignments if a['assignment_success']]),
            'unassigned_flights': len(self.unassigned_flights),
            'teams': self.team_manager.get_team_summary()
        }
        
        return summary
    
    def export_schedule(self, filename="../team_schedule.csv"):
        """Export the schedule to CSV"""
        if not self.assignments:
            print("❌ No assignments to export!")
            return False
        
        export_data = []
        for assignment in self.assignments:
            export_data.append({
                'Flight': assignment['flight_id'],
                'Route': assignment['flight_route'],
                'ETA': assignment['eta'].strftime('%H:%M') if hasattr(assignment['eta'], 'strftime') else str(assignment['eta']),
                'ETD': assignment['etd'].strftime('%H:%M') if hasattr(assignment['etd'], 'strftime') else str(assignment['etd']),
                'Gate': assignment['gate'],
                'Aircraft': assignment['aircraft'],
                'Heaviness': assignment['heaviness'],
                'Team': assignment['team_assigned'] if assignment['team_assigned'] else 'UNASSIGNED',
                'Team Members': ', '.join(assignment['team_members']) if assignment['team_members'] else '',
                'Status': '✅' if assignment['assignment_success'] else '❌'
            })
        
        schedule_df = pd.DataFrame(export_data)
        schedule_df.to_csv(filename, index=False)
        print(f"✅ Schedule exported to {filename}")
        return True
    
    def print_schedule(self):
        """Print the complete schedule"""
        print("\n" + "="*80)
        print("TEAM-BASED FLIGHT SCHEDULE")
        print("="*80)
        
        for assignment in sorted(self.assignments, key=lambda x: x['eta']):
            eta_str = assignment['eta'].strftime('%H:%M') if hasattr(assignment['eta'], 'strftime') else str(assignment['eta'])
            etd_str = assignment['etd'].strftime('%H:%M') if hasattr(assignment['etd'], 'strftime') else str(assignment['etd'])
            
            status = "✅" if assignment['assignment_success'] else "❌"
            team = assignment['team_assigned'] if assignment['team_assigned'] else "UNASSIGNED"
            
            print(f"{status} Flight {assignment['flight_id']:<6} | {eta_str}-{etd_str} | Gate {assignment['gate']:<3} | Team {team:<6} | {assignment['flight_route']}")
        
        # Print team summary
        print("\n" + "="*80)
        print("TEAM WORKLOAD SUMMARY")
        print("="*80)
        
        for team_info in self.team_manager.get_team_summary():
            print(f"Team {team_info['team_name']}: {team_info['flight_count']} flights | {team_info['size']} members | {team_info['current_status']}")
            print(f"   Members: {', '.join(team_info['members'])}")

if __name__ == "__main__":
    print("TeamBasedScheduler class ready!")
    print("Run team-based scheduling with persistent teams")