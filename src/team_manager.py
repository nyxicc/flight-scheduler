import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict

class TeamManager:
    def __init__(self, notification_system=None):
        self.teams = {}  # {'Alpha': {'members': [...], 'flight_count': 0, 'current_flight': None}}
        self.team_names = ['Alpha', 'Bravo', 'Charlie', 'Delta']
        self.pending_changes = []  # Queue of team changes awaiting approval
        self.notification_system = notification_system
        
    def form_initial_teams(self, employees_df, shift_start_time):
        """
        Form initial teams at shift start
        Args:
            employees_df: DataFrame of all employees
            shift_start_time: datetime of when shift starts (e.g., 4:00 AM)
        """
        # Get employees who are working at shift start
        available_employees = employees_df[
            (employees_df['start'] <= shift_start_time) &
            (employees_df['end'] > shift_start_time)
        ].copy()
        
        total_employees = len(available_employees)
        
        if total_employees == 0:
            return None, "No employees available at shift start"
        
        # Determine number of teams and size
        # Prefer 4 people per team, but minimum 3
        ideal_team_size = 4
        min_team_size = 3
        critical_min = 2  # Only in rare cases
        
        # Calculate optimal team configuration
        num_teams, team_sizes = self._calculate_team_distribution(
            total_employees, ideal_team_size, min_team_size, critical_min
        )
        
        # Distribute employees across teams
        employees_list = available_employees.to_dict('records')
        
        # Shuffle for random distribution while maintaining balance
        import random
        random.shuffle(employees_list)
        
        # Form teams
        current_index = 0
        for i in range(num_teams):
            team_name = self.team_names[i]
            team_size = team_sizes[i]
            
            team_members = employees_list[current_index:current_index + team_size]
            current_index += team_size
            
            self.teams[team_name] = {
                'members': team_members,
                'member_ids': [m['employee_id'] for m in team_members],
                'member_names': [m['employee_name'] for m in team_members],
                'flight_count': 0,
                'current_flight': None,
                'last_flight_end': None,
                'size': team_size
            }
        
        # Handle remainder employees (if any)
        remainder_employees = employees_list[current_index:]
        
        return self.teams, remainder_employees
    
    def _calculate_team_distribution(self, total_employees, ideal_size, min_size, critical_min):
        """Calculate optimal number of teams and their sizes"""
        
        # Try for 4 teams first (most operational flexibility)
        if total_employees >= 4 * min_size:  # At least 12 people
            num_teams = 4
        elif total_employees >= 3 * min_size:  # At least 9 people
            num_teams = 3
        elif total_employees >= 2 * min_size:  # At least 6 people
            num_teams = 2
        elif total_employees >= critical_min:  # At least 2 people
            num_teams = 1
        else:
            return 0, []
        
        # Distribute employees as evenly as possible
        base_size = total_employees // num_teams
        remainder = total_employees % num_teams
        
        # Create team sizes (some teams get +1 person)
        team_sizes = [base_size] * num_teams
        for i in range(remainder):
            team_sizes[i] += 1
        
        return num_teams, team_sizes
    
    def get_available_teams(self, flight_time, min_break_minutes=15):
        """
        Get teams available to work a flight at given time
        Args:
            flight_time: datetime of when flight arrives
            min_break_minutes: minimum rest between flights
        """
        available_teams = []
        
        for team_name, team_data in self.teams.items():
            # Check if team is currently on a flight
            if team_data['current_flight'] is not None:
                continue
            
            # Check if team has sufficient break since last flight
            if team_data['last_flight_end'] is not None:
                time_since_last = (flight_time - team_data['last_flight_end']).total_seconds() / 60
                if time_since_last < min_break_minutes:
                    continue
            
            # Check if all team members are still working
            all_available = True
            for member in team_data['members']:
                if member['end'] < flight_time:
                    all_available = False
                    break
            
            if all_available:
                available_teams.append({
                    'name': team_name,
                    'size': team_data['size'],
                    'flight_count': team_data['flight_count'],
                    'members': team_data['member_names']
                })
        
        return available_teams
    
    def assign_team_to_flight(self, team_name, flight):
        """Assign a team to a specific flight"""
        if team_name not in self.teams:
            return False
        
        self.teams[team_name]['current_flight'] = flight
        self.teams[team_name]['flight_count'] += 1
        
        return True
    
    def complete_flight(self, team_name, flight_end_time):
        """Mark a flight as complete for a team"""
        if team_name not in self.teams:
            return False
        
        self.teams[team_name]['current_flight'] = None
        self.teams[team_name]['last_flight_end'] = flight_end_time
        
        return True
    
    def detect_and_notify_changes(self, employees_df, current_time):
        """
        Detect team changes and create notifications
        Checks for employees joining or leaving within 30-minute window
        """
        if not self.notification_system:
            return []
        
        notifications_created = []
        
        for team_name, team_data in self.teams.items():
            # Check for employees whose shifts are ending soon (within 30 mins)
            for member in team_data['members']:
                time_until_end = (member['end'] - current_time).total_seconds() / 60
                
                # Employee is leaving within 30 minutes
                if 0 < time_until_end <= 30:
                    # Check if there's a replacement available
                    # Look for employees who started recently or are starting soon
                    potential_replacements = employees_df[
                        (employees_df['start'] <= current_time) &
                        (employees_df['end'] > current_time + timedelta(minutes=30)) &
                        (~employees_df['employee_id'].isin(team_data['member_ids']))
                    ]
                    
                    if len(potential_replacements) > 0:
                        # Found a replacement
                        replacement = potential_replacements.iloc[0]
                        
                        notif_id = self.notification_system.create_notification(
                            'team_replacement',
                            {
                                'team_name': team_name,
                                'leaving_name': self._flip_name(member['employee_name']),
                                'leaving_id': member['employee_id'],
                                'replacement_time': member['end'].strftime('%H:%M'),
                                'joining_name': self._flip_name(replacement['employee_name']),
                                'joining_id': replacement['employee_id'],
                                'join_time': replacement['start'].strftime('%H:%M'),
                                'joining_shift_start': replacement['start'].strftime('%H:%M'),
                                'joining_shift_end': replacement['end'].strftime('%H:%M')
                            }
                        )
                        notifications_created.append(notif_id)
                    else:
                        # No replacement available
                        remaining_size = len(team_data['members']) - 1
                        
                        notif_id = self.notification_system.create_notification(
                            'team_leave',
                            {
                                'team_name': team_name,
                                'employee_name': self._flip_name(member['employee_name']),
                                'employee_id': member['employee_id'],
                                'leave_time': member['end'].strftime('%H:%M'),
                                'remaining_team_size': remaining_size
                            }
                        )
                        notifications_created.append(notif_id)
            
            # Check for new employees joining (just started working)
            # These are employees who started in the last 5 minutes and aren't on any team
            all_team_member_ids = []
            for t in self.teams.values():
                all_team_member_ids.extend(t['member_ids'])
            
            recent_arrivals = employees_df[
                (employees_df['start'] <= current_time) &
                (employees_df['start'] >= current_time - timedelta(minutes=5)) &
                (~employees_df['employee_id'].isin(all_team_member_ids))
            ]
            
            for _, new_employee in recent_arrivals.iterrows():
                # Check if any team needs this person (size below optimal)
                suggested_team = None
                for t_name, t_data in self.teams.items():
                    if t_data['size'] < 4:  # Team is below optimal size
                        suggested_team = t_name
                        break
                
                notif_id = self.notification_system.create_notification(
                    'team_join',
                    {
                        'employee_name': self._flip_name(new_employee['employee_name']),
                        'employee_id': new_employee['employee_id'],
                        'team_name': suggested_team if suggested_team else 'TBD',
                        'shift_start': new_employee['start'].strftime('%H:%M'),
                        'shift_end': new_employee['end'].strftime('%H:%M'),
                        'total_hours': new_employee.get('total_hours', 0),
                        'suggested_team': suggested_team
                    }
                )
                notifications_created.append(notif_id)
        
        return notifications_created
    
    def _flip_name(self, full_name):
        """Convert 'LastName, FirstName' to 'FirstName LastName'"""
        if ', ' in str(full_name):
            last, first = full_name.split(', ', 1)
            return f"{first} {last}"
        return full_name
    
    def apply_team_change(self, change, approved=True):
        """Apply an approved team change"""
        if not approved:
            return False
        
        team_name = change['team']
        
        if change['type'] == 'replacement':
            # Remove leaving member
            self.teams[team_name]['members'] = [
                m for m in self.teams[team_name]['members'] 
                if m['employee_id'] != change['leaving']['employee_id']
            ]
            
            # Add joining member
            self.teams[team_name]['members'].append(change['joining'])
            self.teams[team_name]['member_ids'] = [m['employee_id'] for m in self.teams[team_name]['members']]
            self.teams[team_name]['member_names'] = [m['employee_name'] for m in self.teams[team_name]['members']]
            
        elif change['type'] == 'leaving':
            # Just remove the leaving member
            self.teams[team_name]['members'] = [
                m for m in self.teams[team_name]['members'] 
                if m['employee_id'] != change['leaving']['employee_id']
            ]
            self.teams[team_name]['member_ids'] = [m['employee_id'] for m in self.teams[team_name]['members']]
            self.teams[team_name]['member_names'] = [m['employee_name'] for m in self.teams[team_name]['members']]
            self.teams[team_name]['size'] = len(self.teams[team_name]['members'])
        
        return True
    
    def get_team_summary(self):
        """Get summary of all teams for display"""
        summary = []
        for team_name, team_data in self.teams.items():
            summary.append({
                'team_name': team_name,
                'size': team_data['size'],
                'members': team_data['member_names'],
                'flight_count': team_data['flight_count'],
                'current_status': 'On Flight' if team_data['current_flight'] else 'Available'
            })
        return summary
    
    def manually_swap_members(self, team1_name, team2_name, employee_id):
        """Manually move an employee from one team to another"""
        if team1_name not in self.teams or team2_name not in self.teams:
            return False
        
        # Find employee in team1
        employee = None
        for member in self.teams[team1_name]['members']:
            if member['employee_id'] == employee_id:
                employee = member
                break
        
        if not employee:
            return False
        
        # Remove from team1
        self.teams[team1_name]['members'] = [
            m for m in self.teams[team1_name]['members'] 
            if m['employee_id'] != employee_id
        ]
        self.teams[team1_name]['size'] = len(self.teams[team1_name]['members'])
        
        # Add to team2
        self.teams[team2_name]['members'].append(employee)
        self.teams[team2_name]['size'] = len(self.teams[team2_name]['members'])
        
        # Update IDs and names
        for team_name in [team1_name, team2_name]:
            self.teams[team_name]['member_ids'] = [m['employee_id'] for m in self.teams[team_name]['members']]
            self.teams[team_name]['member_names'] = [m['employee_name'] for m in self.teams[team_name]['members']]
        
        return True

if __name__ == "__main__":
    print("TeamManager class ready!")
    print("Handles persistent team formation and management")