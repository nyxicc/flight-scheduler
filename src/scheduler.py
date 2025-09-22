import pandas as pd
from datetime import datetime
import numpy as np

class Scheduler:
    def __init__(self, employee_handler, flight_handler):
        """
        Initialize the Scheduler with employee and flight handlers
        
        Args:
            employee_handler: Instance of EmployeeHandler class
            flight_handler: Instance of FlightHandler class
        """
        self.employee_handler = employee_handler
        self.flight_handler = flight_handler
        self.assignments = []
        self.scheduling_results = {
            'successful_assignments': 0,
            'failed_assignments': 0,
            'total_positions_filled': 0,
            'unassigned_flights': []
        }
    
    def run_scheduling(self):
        """
        Main scheduling method that assigns teams to all flights
        """
        print("🚀 STARTING FLIGHT TEAM SCHEDULING")
        print("="*60)
        
        # Reset previous scheduling results
        self.assignments = []
        self.scheduling_results = {
            'successful_assignments': 0,
            'failed_assignments': 0,
            'total_positions_filled': 0,
            'unassigned_flights': []
        }
        
        # Get all employees and flights
        if self.employee_handler.employees_df is None:
            print("❌ No employee data loaded!")
            return False
            
        if self.flight_handler.flights_df is None:
            print("❌ No flight data loaded!")
            return False
        
        # Reset employee workloads at start of scheduling
        self.employee_handler.reset_workload()
        
        # Get flights and sort by team size needed (heaviest first)
        flights_df = self.flight_handler.flights_df.copy()
        
        # Add team size column for sorting
        flights_df['required_team_size'] = flights_df['heaviness'].apply(
            lambda x: self.flight_handler.get_team_size_needed(x)
        )
        
        # Sort flights: Heavy flights first (need bigger teams)
        flights_sorted = flights_df.sort_values(
            ['required_team_size', 'eta_datetime'], 
            ascending=[False, True]
        )
        
        print(f"📋 Processing {len(flights_sorted)} flights...")
        print(f"👥 Available employees: {len(self.employee_handler.employees_df)}")
        print(f"⏰ Flight time range: {flights_sorted['eta_datetime'].min().strftime('%H:%M')} - {flights_sorted['eta_datetime'].max().strftime('%H:%M')}")
        print("\n" + "="*60)
        print("FLIGHT ASSIGNMENT PROCESS")
        print("="*60)
        
        # Process each flight
        for index, flight in flights_sorted.iterrows():
            self._assign_flight(flight)
        
        # Print final results
        self._print_scheduling_summary()
        
        return len(self.assignments) > 0
    
    def _assign_flight(self, flight):
        """
        Assign a team to a specific flight
        
        Args:
            flight: Flight row from flights DataFrame
        """
        flight_id = flight.get('flight_number', 'Unknown')
        heaviness = flight.get('heaviness', 'Medium')
        eta = flight.get('eta_datetime', 'Unknown')
        etd = flight.get('etd_datetime', 'Unknown')
        gate = flight.get('gate', 'Unknown')
        
        required_team_size = self.flight_handler.get_team_size_needed(heaviness)
        
        print(f"✈️  Processing Flight {flight_id}")
        print(f"    Route: {flight.get('city', 'Unknown')} → {flight.get('outbound_city', 'Unknown')}")
        print(f"    Aircraft: {flight.get('aircraft', 'Unknown')}")
        print(f"    Time: {eta.strftime('%H:%M') if hasattr(eta, 'strftime') else eta} - {etd.strftime('%H:%M') if hasattr(etd, 'strftime') else etd}")
        print(f"    Heaviness: {heaviness} (needs {required_team_size} people)")
        print(f"    Gate: {gate}")
        
        # Find available employees for this flight time
        available_employees = self.employee_handler.find_available_employees(eta, etd)
        
        if len(available_employees) == 0:
            print(f"    ❌ No employees available for this time slot")
            self._record_failed_assignment(flight, "No employees available for time slot")
            return
        
        print(f"    👥 {len(available_employees)} employees available for this time")
        
        # Find the best team
        selected_team = self.find_best_team(required_team_size, available_employees)
        
        if len(selected_team) < required_team_size:
            print(f"    ❌ Only {len(selected_team)}/{required_team_size} employees available")
            self._record_failed_assignment(flight, f"Insufficient employees: {len(selected_team)}/{required_team_size}")
            return
        
        # Assign the team
        team_names = []
        for emp_id in selected_team:
            self.employee_handler.assign_flight_to_employee(emp_id)
            emp_name = self.employee_handler.employees_df[
                self.employee_handler.employees_df['employee_id'] == emp_id
            ]['employee_name'].iloc[0]
            team_names.append(emp_name)
        
        # Record the assignment
        assignment = {
            'flight_id': flight_id,
            'inbound_city': flight.get('city', 'Unknown'),
            'outbound_city': flight.get('outbound_city', 'Unknown'),
            'aircraft': flight.get('aircraft', 'Unknown'),
            'flight_route': f"{flight.get('city', 'Unknown')} → {flight.get('outbound_city', 'Unknown')}",
            'eta': eta,
            'etd': etd,
            'gate': gate,
            'heaviness': heaviness,
            'turnaround_minutes': flight.get('turnaround_minutes', 0),
            'required_team_size': required_team_size,
            'assigned_team_size': len(selected_team),
            'team_ids': selected_team,
            'team_names': team_names,
            'assignment_success': True
        }
        
        self.assignments.append(assignment)
        self.scheduling_results['successful_assignments'] += 1
        self.scheduling_results['total_positions_filled'] += len(selected_team)
        
        print(f"    ✅ SUCCESS! Assigned team: {', '.join(team_names)}")
        print()
    
    def find_best_team(self, required_size, available_employees):
        """
        Find the best team from available employees
        
        Args:
            required_size: Number of employees needed
            available_employees: DataFrame of available employees
            
        Returns:
            List of employee IDs for the selected team
        """
        if len(available_employees) < required_size:
            return []
        
        # Create a copy with current workload information
        team_candidates = available_employees.copy()
        
        # Add current workload to the dataframe
        team_candidates['current_workload'] = team_candidates['employee_id'].map(
            lambda x: self.employee_handler.workload_tracker.get(x, 0)
        )
        
        # Sort by current workload (lowest first)
        team_candidates_sorted = team_candidates.sort_values(
            'current_workload',    # Lowest workload first (primary)
            ascending=True
        )
        
        # Select the top candidates
        selected_team = team_candidates_sorted.head(required_size)
        
        return selected_team['employee_id'].tolist()
    
    def _record_failed_assignment(self, flight, reason):
        """Record a failed flight assignment"""
        flight_id = flight.get('flight_number', 'Unknown')
        
        failed_assignment = {
            'flight_id': flight_id,
            'inbound_city': flight.get('city', 'Unknown'),
            'outbound_city': flight.get('outbound_city', 'Unknown'),
            'aircraft': flight.get('aircraft', 'Unknown'),
            'flight_route': f"{flight.get('city', 'Unknown')} → {flight.get('outbound_city', 'Unknown')}",
            'eta': flight.get('eta_datetime', 'Unknown'),
            'etd': flight.get('etd_datetime', 'Unknown'),
            'gate': flight.get('gate', 'Unknown'),
            'heaviness': flight.get('heaviness', 'Medium'),
            'turnaround_minutes': flight.get('turnaround_minutes', 0),
            'required_team_size': self.flight_handler.get_team_size_needed(flight.get('heaviness', 'Medium')),
            'failure_reason': reason,
            'assignment_success': False
        }
        
        self.assignments.append(failed_assignment)
        self.scheduling_results['failed_assignments'] += 1
        self.scheduling_results['unassigned_flights'].append(flight_id)
    
    def _print_scheduling_summary(self):
        """Print a summary of the scheduling results"""
        print("\n" + "="*60)
        print("📊 SCHEDULING SUMMARY")
        print("="*60)
        
        total_flights = len(self.assignments)
        successful = self.scheduling_results['successful_assignments']
        failed = self.scheduling_results['failed_assignments']
        
        print(f"Total Flights Processed: {total_flights}")
        print(f"✅ Successfully Assigned: {successful} ({successful/total_flights*100:.1f}%)")
        print(f"❌ Failed Assignments: {failed} ({failed/total_flights*100:.1f}%)")
        print(f"👥 Total Team Positions Filled: {self.scheduling_results['total_positions_filled']}")
        
        if failed > 0:
            print(f"\n⚠️  Unassigned Flights: {', '.join(map(str, self.scheduling_results['unassigned_flights']))}")
        
        # Employee workload summary
        workload_summary = self.employee_handler.get_workload_summary()
        if workload_summary is not None:
            avg_utilization = workload_summary['utilization_pct'].mean()
            max_utilization = workload_summary['utilization_pct'].max()
            print(f"\n👥 EMPLOYEE UTILIZATION:")
            print(f"Average Utilization: {avg_utilization:.1f}%")
            print(f"Peak Utilization: {max_utilization:.1f}%")
            
            # Show employees at capacity
            overworked = workload_summary[workload_summary['utilization_pct'] >= 100]
            if len(overworked) > 0:
                print(f"⚠️  Employees at/over capacity: {len(overworked)}")
    
    def get_assignments_dataframe(self):
        """Return assignments as a pandas DataFrame"""
        if not self.assignments:
            return pd.DataFrame()
        
        return pd.DataFrame(self.assignments)
    
    def export_schedule(self, filename="daily_schedule.csv"):
        """Export the complete schedule to CSV"""
        if not self.assignments:
            print("❌ No assignments to export!")
            return False
        
        schedule_df = self.get_assignments_dataframe()
        schedule_df.to_csv(filename, index=False)
        print(f"✅ Schedule exported to {filename}")
        return True
    
    def get_schedule_by_employee(self):
        """Get schedule organized by employee (useful for individual schedules)"""
        if not self.assignments:
            return {}
        
        employee_schedules = {}
        
        for assignment in self.assignments:
            if assignment['assignment_success']:
                for i, emp_id in enumerate(assignment['team_ids']):
                    emp_name = assignment['team_names'][i]
                    
                    if emp_id not in employee_schedules:
                        employee_schedules[emp_id] = {
                            'employee_name': emp_name,
                            'flights': []
                        }
                    
                    employee_schedules[emp_id]['flights'].append({
                        'flight_id': assignment['flight_id'],
                        'inbound_city': assignment['inbound_city'],
                        'outbound_city': assignment['outbound_city'],
                        'aircraft': assignment['aircraft'],
                        'route': assignment['flight_route'],
                        'eta': assignment['eta'],
                        'etd': assignment['etd'],
                        'gate': assignment['gate'],
                        'heaviness': assignment['heaviness'],
                        'turnaround_minutes': assignment['turnaround_minutes']
                    })
        
        return employee_schedules
    
    def print_employee_schedules(self):
        """Print individual employee schedules"""
        employee_schedules = self.get_schedule_by_employee()
        
        if not employee_schedules:
            print("❌ No employee schedules available!")
            return
        
        print("\n" + "="*60)
        print("👥 INDIVIDUAL EMPLOYEE SCHEDULES")
        print("="*60)
        
        for emp_id, schedule in employee_schedules.items():
            print(f"\n{schedule['employee_name']} ({emp_id}):")
            print(f"  Flights assigned: {len(schedule['flights'])}")
            
            for flight in sorted(schedule['flights'], key=lambda x: x['eta']):
                eta_time = flight['eta'].strftime('%H:%M') if hasattr(flight['eta'], 'strftime') else flight['eta']
                etd_time = flight['etd'].strftime('%H:%M') if hasattr(flight['etd'], 'strftime') else flight['etd']
                turnaround = f" ({flight['turnaround_minutes']:.0f}min)" if flight['turnaround_minutes'] else ""
                print(f"    • Flight {flight['flight_id']} ({flight['heaviness']})")
                print(f"      {flight['route']} | {eta_time}-{etd_time}{turnaround} | Gate {flight['gate']} | {flight['aircraft']}")

if __name__ == "__main__":
    print("Scheduler class ready!")
    print("To use: import this file and create Scheduler(employee_handler, flight_handler)")
    print("Then call scheduler.run_scheduling()")