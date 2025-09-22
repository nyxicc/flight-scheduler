from employee_handler import EmployeeHandler
from flight_handler import FlightHandler
from scheduler import Scheduler

def main():
    """
    Main function to run the United Ground Express Flight Team Scheduler
    """
    print("UNITED GROUND EXPRESS - FLIGHT TEAM SCHEDULER")
    print("=" * 70)
    print("Automated team assignment system for Nashville operations")
    print()
    
    # Initialize the handlers
    print("Initializing system components...")
    employee_handler = EmployeeHandler()
    flight_handler = FlightHandler()
    
    # Load employee data
    print("\n" + "=" * 50)
    print("LOADING EMPLOYEE DATA")
    print("=" * 50)
    employee_success = employee_handler.load_employees("data/employees.csv")
    
    if not employee_success:
        print("Failed to load employee data. Please check your data/employees.csv file.")
        print("Make sure the file exists and has columns: Employee, Start, End, Hours")
        return
    
    # Load flight data
    print("\n" + "=" * 50)
    print("LOADING FLIGHT DATA")
    print("=" * 50)
    flight_success = flight_handler.load_flights("data/flights.csv")
    
    if not flight_success:
        print("Failed to load flight data. Please check your data/flights.csv file.")
        print("Make sure the file exists and has columns: FLT#, CTY, ETA, ETD, etc.")
        return
    
    # Apply Nashville-specific heaviness rules (Method 2)
    print("\n" + "=" * 50)
    print("APPLYING NASHVILLE HEAVINESS RULES")
    print("=" * 50)
    
    nashville_city_rules = {
        # Heavy workload cities
        'DEN': 'Medium',    # Denver - long distance, more cargo
        'LAX': 'Heavy',    # Los Angeles - high volume
        'EWR': 'Light',    # Newark - complex operations
        'JFK': 'Heavy',    # JFK - international, complex
        'LGA': 'Heavy',    # LaGuardia - tight schedules
        'SFO': 'Medium',    # San Francisco - high volume
        
        # Medium workload cities  
        'IAH': 'Medium',   # Houston - moderate operations
        'DFW': 'Medium',   # Dallas - moderate operations
        'ATL': 'Medium',   # Atlanta - standard operations
        'CLT': 'Medium',   # Charlotte - standard operations
        'IAD': 'Medium',   # Washington Dulles - standard
        'BWI': 'Medium',   # Baltimore - standard
        'PHX': 'Heavy',   # Phoenix - standard
        
        # Light workload cities
        'ORD': 'Light',    # Chicago O'Hare - efficient operations
        'MDW': 'Light',    # Chicago Midway - smaller operations
        'SEA': 'Heavy',    # Seattle - efficient turnarounds
        'PDX': 'Heavy',    # Portland - smaller operations
        'MSY': 'Light',    # New Orleans - local operations
        'MEM': 'Light',    # Memphis - regional hub
        'STL': 'Light',    # St. Louis - regional operations
    }
    
    # Apply the heaviness rules
    flight_handler.set_manual_heaviness_by_city(nashville_city_rules)
    
    # Show flight summary with applied heaviness
    flight_handler.show_flight_summary()
    flight_handler.show_heaviness_summary()
    
    # Show employee summary
    employee_handler.show_employee_summary()
    
    # Create and run the scheduler
    print("\n" + "=" * 50)
    print("CREATING SCHEDULER")
    print("=" * 50)
    
    scheduler = Scheduler(employee_handler, flight_handler)
    
    print("Starting automated team assignments...")
    print("Priority: Heavy flights first, then workload balancing")
    print()
    
    # Run the scheduling algorithm
    scheduling_success = scheduler.run_scheduling()
    
    if scheduling_success:
        print("\n" + "=" * 50)
        print("EXPORTING RESULTS")
        print("=" * 50)
        
        # Export the main schedule
        scheduler.export_schedule("daily_schedule.csv")
        
        # Print individual employee schedules
        scheduler.print_employee_schedules()
        
        # Show final workload summary
        print("\n" + "=" * 50)
        print("FINAL WORKLOAD ANALYSIS")
        print("=" * 50)
        
        workload_summary = employee_handler.get_workload_summary()
        if workload_summary is not None:
            print("Employee workload distribution:")
            print(workload_summary[['employee_name', 'current_flights', 'max_flights', 'utilization_pct']].to_string(index=False))
            
            # Check for any issues
            overworked = workload_summary[workload_summary['utilization_pct'] > 100]
            underutilized = workload_summary[workload_summary['utilization_pct'] < 30]
            
            if len(overworked) > 0:
                print(f"\nWARNING: {len(overworked)} employees are over capacity!")
                print("Consider hiring more staff or redistributing flights.")
                
            if len(underutilized) > 0:
                print(f"\nINFO: {len(underutilized)} employees are under 30% utilization.")
                print("These employees could potentially take on more flights.")
        
        print("\n" + "=" * 70)
        print("SCHEDULING COMPLETE!")
        print("=" * 70)
        print("Files created:")
        print("  - daily_schedule.csv (complete flight assignments)")
        print("Check the output above for individual employee schedules.")
        
    else:
        print("\n" + "=" * 50)
        print("SCHEDULING FAILED")
        print("=" * 50)
        print("Common issues:")
        print("  - Not enough employees for the number of flights")
        print("  - Employee shift times don't match flight times")
        print("  - Too many heavy flights requiring large teams")
        print("\nRecommendations:")
        print("  - Check that employee shift times cover all flight times")
        print("  - Consider adjusting flight heaviness rules")
        print("  - Add more employees if workload is too high")

def customize_heaviness_rules():
    """
    Helper function to easily customize heaviness rules for different airports
    """
    print("CUSTOMIZING HEAVINESS RULES")
    print("=" * 40)
    print("Current Nashville rules prioritize:")
    print("HEAVY: Denver, LA, Newark, JFK (complex operations)")
    print("MEDIUM: Houston, Atlanta, Phoenix (standard operations)")  
    print("LIGHT: Chicago, Seattle, regional airports (efficient ops)")
    print("\nTo modify rules, edit the nashville_city_rules dictionary in main()")
    print("Available levels: 'Heavy' (5 people), 'Medium' (4 people), 'Light' (3 people)")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScheduling interrupted by user.")
    except Exception as e:
        print(f"\nERROR: An unexpected error occurred: {e}")
        print("Please check your CSV files and try again.")
        print("\nFor help:")
        print("  - Ensure data/employees.csv and data/flights.csv exist")
        print("  - Check that CSV files have the correct column headers")
        print("  - Make sure employee shift times are in datetime format")
        print("  - Verify flight times are in HH:MM format")