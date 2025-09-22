import pandas as pd
from datetime import datetime
import numpy as np

class EmployeeHandler:
    def __init__(self):
        self.employees_df = None
        self.workload_tracker = {}
        
    def load_employees(self, file_path="employees.csv"):
        """Load employee data from your CSV file"""
        try:
            # Load the CSV
            self.employees_df = pd.read_csv(file_path)
            
            # Handle your actual column names from the website
            column_mapping = {
                'Date': 'date',
                'Position': 'position',
                'Employee': 'employee_name',
                'Group': 'group',
                'Notes': 'notes', 
                'Start': 'start_time',
                'End': 'end_time',
                'Break': 'break_info',
                'Hours': 'total_hours'
            }
            
            # Rename columns to match our internal structure
            self.employees_df = self.employees_df.rename(columns=column_mapping)
            
            # Remove rows where employee_name is empty or contains special markers like ---EMPTY---
            self.employees_df = self.employees_df[self.employees_df['employee_name'].notna()]
            self.employees_df = self.employees_df[~self.employees_df['employee_name'].str.contains('EMPTY', na=False, case=False)]
            
            # Combine Date with Start and End times to create full datetime
            # Your format: Date column (9/13/2025) + Start column (9:00:00 AM) or (12:00:00 PM)
            if 'date' in self.employees_df.columns and 'start_time' in self.employees_df.columns:
                # Create full datetime strings
                self.employees_df['start'] = pd.to_datetime(
                    self.employees_df['date'].astype(str) + ' ' + self.employees_df['start_time'].astype(str),
                    errors='coerce'
                )
                self.employees_df['end'] = pd.to_datetime(
                    self.employees_df['date'].astype(str) + ' ' + self.employees_df['end_time'].astype(str),
                    errors='coerce'
                )
            else:
                # Fallback if format is different
                self.employees_df['start'] = pd.to_datetime(self.employees_df['start_time'], errors='coerce')
                self.employees_df['end'] = pd.to_datetime(self.employees_df['end_time'], errors='coerce')
            
            # Remove any rows with invalid datetime conversions
            self.employees_df = self.employees_df.dropna(subset=['start', 'end'])
            
            # Add employee_id if not present
            if 'employee_id' not in self.employees_df.columns:
                self.employees_df['employee_id'] = ['EMP' + str(i+1).zfill(3) for i in range(len(self.employees_df))]
            
            # Add max_flights_per_day if not present
            if 'max_flights_per_day' not in self.employees_df.columns:
                if 'total_hours' in self.employees_df.columns:
                    # Estimate: 1 flight per 2-3 hours of work
                    self.employees_df['max_flights_per_day'] = (self.employees_df['total_hours'] / 2.5).round().astype(int).clip(lower=1, upper=6)
                else:
                    self.employees_df['max_flights_per_day'] = 4  # Default
            
            # Initialize workload tracking
            self.workload_tracker = {emp_id: 0 for emp_id in self.employees_df['employee_id']}
            
            print("✓ Employee data loaded successfully!")
            print(f"  Total employees: {len(self.employees_df)}")
            print(f"  Date/Time range: {self.employees_df['start'].min()} to {self.employees_df['end'].max()}")
            if 'total_hours' in self.employees_df.columns:
                print(f"  Average hours: {self.employees_df['total_hours'].mean():.1f}")
            return True
            
        except FileNotFoundError:
            print(f"❌ File '{file_path}' not found!")
            print("Please make sure your employees.csv is in the correct location.")
            return False
        except Exception as e:
            print(f"❌ Error loading employee data: {e}")
            print("Data preview:")
            try:
                preview_df = pd.read_csv(file_path)
                print(preview_df.head())
                print(f"Columns: {list(preview_df.columns)}")
            except:
                pass
            return False
    
    def show_employee_summary(self):
        """Display a summary of loaded employee data"""
        if self.employees_df is None:
            print("❌ No employee data loaded!")
            return
        
        print("\n" + "="*60)
        print("EMPLOYEE DATA SUMMARY")
        print("="*60)
        
        # Basic stats
        print(f"Total Employees: {len(self.employees_df)}")
        
        if 'total_hours' in self.employees_df.columns:
            print(f"Average Hours: {self.employees_df['total_hours'].mean():.1f}")
            print(f"Total Hours (All Employees): {self.employees_df['total_hours'].sum():.1f}")
            print(f"Hours Range: {self.employees_df['total_hours'].min():.1f} - {self.employees_df['total_hours'].max():.1f}")
        
        if 'group' in self.employees_df.columns:
            group_counts = self.employees_df['group'].value_counts()
            print(f"\nGroup Distribution:")
            for group, count in group_counts.items():
                if pd.notna(group):  # Skip NaN groups
                    print(f"  {group}: {count} employees")
        
        # Show sample data
        print(f"\nSample Employee Records:")
        display_cols = ['employee_name', 'total_hours', 'max_flights_per_day', 'start', 'end']
        available_cols = [col for col in display_cols if col in self.employees_df.columns]
        print(self.employees_df[available_cols].head().to_string(index=False))
    
    def find_available_employees(self, flight_start, flight_end):
        """Find employees available for a specific flight time (using your logic)"""
        if self.employees_df is None:
            print("❌ No employee data loaded!")
            return pd.DataFrame()
        
        # Convert strings to datetime if needed
        if isinstance(flight_start, str):
            flight_start = pd.to_datetime(flight_start)
        if isinstance(flight_end, str):
            flight_end = pd.to_datetime(flight_end)
        
        # Your existing availability logic
        available_employees = self.employees_df[
            (self.employees_df['start'] <= flight_start) &
            (self.employees_df['end'] >= flight_end)
        ]
        
        # Also filter by workload capacity
        available_with_capacity = available_employees[
            available_employees['employee_id'].map(
                lambda x: self.workload_tracker[x] < self.employees_df[self.employees_df['employee_id'] == x]['max_flights_per_day'].iloc[0]
            )
        ]
        
        return available_with_capacity
    
    def assign_flight_to_employee(self, employee_id):
        """Assign a flight to an employee (increment their workload)"""
        if employee_id in self.workload_tracker:
            self.workload_tracker[employee_id] += 1
            return True
        return False
    
    def reset_workload(self):
        """Reset all employee workloads to 0"""
        self.workload_tracker = {emp_id: 0 for emp_id in self.employees_df['employee_id']}
        print("✓ Employee workloads reset")
    
    def get_workload_summary(self):
        """Get current workload summary"""
        if self.employees_df is None:
            return None
        
        workload_data = []
        for _, employee in self.employees_df.iterrows():
            emp_id = employee['employee_id']
            workload_data.append({
                'employee_id': emp_id,
                'employee_name': employee.get('employee_name', 'Unknown'),
                'current_flights': self.workload_tracker[emp_id],
                'max_flights': employee['max_flights_per_day'],
                'utilization_pct': (self.workload_tracker[emp_id] / employee['max_flights_per_day']) * 100
            })
        
        return pd.DataFrame(workload_data)
    
    def test_availability(self, test_flight_start="2025-09-13 10:00", test_flight_end="2025-09-13 14:00"):
        """Test employee availability for a sample flight"""
        print(f"\n" + "="*60)
        print(f"TESTING AVAILABILITY")
        print(f"Flight Time: {test_flight_start} to {test_flight_end}")
        print("="*60)
        
        available = self.find_available_employees(test_flight_start, test_flight_end)
        
        if len(available) == 0:
            print("❌ No employees available for this flight time!")
            print("\nAll employee shift times:")
            for _, emp in self.employees_df.iterrows():
                print(f"  {emp['employee_name']}: {emp['start'].strftime('%Y-%m-%d %H:%M')} to {emp['end'].strftime('%Y-%m-%d %H:%M')} ({emp.get('total_hours', 0)} hrs)")
        else:
            print(f"✓ {len(available)} employees available:")
            display_cols = ['employee_name', 'start', 'end', 'total_hours']
            available_cols = [col for col in display_cols if col in available.columns]
            
            # Format the datetime display for better readability
            display_df = available[available_cols].copy()
            if 'start' in display_df.columns:
                display_df['start'] = display_df['start'].dt.strftime('%Y-%m-%d %H:%M')
            if 'end' in display_df.columns:
                display_df['end'] = display_df['end'].dt.strftime('%Y-%m-%d %H:%M')
            
            print(display_df.to_string(index=False))
        
        return available

if __name__ == "__main__":
    print("EmployeeHandler class ready!")
    print("To use: import this file and create EmployeeHandler()")
    print("Then call employee_handler.load_employees('your_file.csv')")