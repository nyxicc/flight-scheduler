import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time

# Import your classes
try:
    from employee_handler import EmployeeHandler
    from flight_handler import FlightHandler
    from scheduler import TeamBasedScheduler
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    st.stop()

# Configure page
st.set_page_config(
    page_title="Flight Team Scheduler",
    page_icon="✈️",
    layout="wide"
)

# Helper function
def flip_name(full_name):
    """Convert 'LastName, FirstName' to 'FirstName LastName'"""
    if ', ' in str(full_name):
        last, first = full_name.split(', ', 1)
        return f"{first} {last}"
    return full_name

# Initialize session state
if 'scheduler' not in st.session_state:
    st.session_state.scheduler = None
if 'teams_approved' not in st.session_state:
    st.session_state.teams_approved = False
if 'shift_start_time' not in st.session_state:
    st.session_state.shift_start_time = None
if 'current_time' not in st.session_state:
    st.session_state.current_time = None

# Main title
st.title("🛫 United Ground Express - Team Scheduler")
st.markdown("*Nashville Operations - Team-Based Scheduling*")

# Sidebar
st.sidebar.header("Control Panel")

# Initialize system
if st.sidebar.button("Initialize New Shift", type="primary"):
    with st.spinner("Loading data and initializing teams..."):
        try:
            # Load handlers
            employee_handler = EmployeeHandler()
            flight_handler = FlightHandler()
            
            employee_success = employee_handler.load_employees("../data/employees.csv")
            flight_success = flight_handler.load_flights("../data/flights.csv")
            
            if not employee_success or not flight_success:
                st.error("Failed to load CSV files")
            else:
                # Apply heaviness rules
                nashville_rules = {
                    'DEN': 'Medium', 'LAX': 'Medium', 'EWR': 'Light', 'JFK': 'Medium',
                    'SFO': 'Medium', 'IAH': 'Medium', 'ORD': 'Light', 'SEA': 'Medium'
                }
                flight_handler.set_manual_heaviness_by_city(nashville_rules)
                
                # Create scheduler
                scheduler = TeamBasedScheduler(employee_handler, flight_handler)
                
                # Set shift start time (get from first employee start time)
                shift_start = employee_handler.employees_df['start'].min()
                
                # Initialize teams
                success, remainder = scheduler.initialize_shift(shift_start)
                
                if success:
                    st.session_state.scheduler = scheduler
                    st.session_state.shift_start_time = shift_start
                    st.session_state.current_time = shift_start
                    st.session_state.teams_approved = False
                    
                    if remainder:
                        st.warning(f"{len(remainder)} employees need team assignment")
                    
                    st.success("Teams formed! Please review and approve.")
                    st.rerun()
                else:
                    st.error("Failed to initialize teams")
        
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Main content
if st.session_state.scheduler is None:
    st.info("Click 'Initialize New Shift' to begin")
    st.markdown("""
    ### System Overview:
    1. **Initialize Shift** - Forms 2-4 persistent teams (Alpha, Bravo, Charlie, Delta)
    2. **Review Teams** - Manually adjust team composition before approval
    3. **Approve Teams** - Lock teams and begin operations
    4. **Automatic Assignment** - Teams assigned to flights in 4-hour rolling window
    5. **Monitor Notifications** - Approve team changes as employees join/leave shifts
    """)

else:
    scheduler = st.session_state.scheduler
    
    # Team approval flow
    if not st.session_state.teams_approved:
        st.header("Pre-Approval: Review Teams and Flight Schedule")
        
        # Show all flights in table format
        st.subheader("Today's Flight Schedule")
        
        flights_df = scheduler.flight_handler.flights_df
        
        # Create display table
        flight_table_data = []
        for _, flight in flights_df.iterrows():
            flight_table_data.append({
                'Arrival Flight #': flight['flight_number'],
                'Departure Flight #': flight.get('outbound_flight', 'N/A'),
                'Gate': flight.get('gate', 'N/A'),
                'ETA': flight['eta_datetime'].strftime('%H:%M') if hasattr(flight['eta_datetime'], 'strftime') else str(flight.get('eta', 'N/A')),
                'ETD': flight['etd_datetime'].strftime('%H:%M') if hasattr(flight['etd_datetime'], 'strftime') else str(flight.get('etd', 'N/A')),
                'Inbound City': flight.get('city', 'N/A'),
                'Outbound City': flight.get('outbound_city', 'N/A'),
                'Heaviness': flight.get('heaviness', 'Medium')
            })
        
        flight_table_df = pd.DataFrame(flight_table_data)
        st.dataframe(flight_table_df, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Show proposed teams
        st.subheader("Proposed Ramp Teams")
        
        teams = scheduler.team_manager.teams
        
<<<<<<< HEAD
        # Display proposed teams
=======
>>>>>>> d0302a760712868c0ae3479513f7e1d11cbd12c1
        if len(teams) == 0:
            st.error("No teams were formed. Check if employees are available at shift start time.")
        else:
            cols = st.columns(len(teams))
            for idx, (team_name, team_data) in enumerate(teams.items()):
                with cols[idx]:
<<<<<<< HEAD
                    st.subheader(f"Team {team_name}")
                    st.write(f"**Size:** {team_data['size']} members")
=======
                    st.markdown(f"**Team {team_name}**")
                    st.write(f"Size: {team_data['size']} members")
>>>>>>> d0302a760712868c0ae3479513f7e1d11cbd12c1
                    
                    for i, member_name in enumerate(team_data['member_names'], 1):
                        st.write(f"{i}. {flip_name(member_name)}")
        
        # Manual team adjustment
        st.divider()
        st.subheader("Manual Team Adjustments")
        
        if len(teams) > 0:
            col1, col2, col3 = st.columns(3)
            
            employee_id = None  # Initialize outside the block
            
            with col1:
                from_team = st.selectbox("From Team:", list(teams.keys()), key="from_team")
            with col2:
                # Get members of selected team
                if from_team in teams:
                    member_names = [flip_name(m) for m in teams[from_team]['member_names']]
                    if member_names:  # Check if team has members
                        selected_member = st.selectbox("Employee:", member_names, key="employee_move")
                        # Find the employee_id for the selected name
                        for member in teams[from_team]['members']:
                            if flip_name(member['employee_name']) == selected_member:
                                employee_id = member['employee_id']
                                break
            with col3:
                to_team = st.selectbox("To Team:", [t for t in teams.keys() if t != from_team], key="to_team")
            
            if st.button("Swap Employee"):
                if employee_id:
                    success = scheduler.team_manager.manually_swap_members(from_team, to_team, employee_id)
                    if success:
                        st.success(f"Moved employee from Team {from_team} to Team {to_team}")
                        st.rerun()
                    else:
                        st.error("Failed to swap employee")
                else:
                    st.warning("No employee selected or team is empty")
        
        # Approve teams
        st.divider()
        if st.button("Approve Teams and Begin Flight Assignments", type="primary", use_container_width=True):
            st.session_state.teams_approved = True
            st.success("Teams approved! You can now assign teams to flights.")
            st.rerun()
    
    else:
        # Operations mode - teams are approved
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "✈️ Flight Schedule", "👥 Teams", "🔔 Notifications"])
        
        with tab1:
            st.header("Operations Dashboard")
            
            # Current time control
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**Current Time:** {st.session_state.current_time.strftime('%Y-%m-%d %H:%M')}")
            with col2:
                if st.button("Advance 5 Minutes"):
                    st.session_state.current_time += timedelta(minutes=5)
                    # Check for team changes
                    scheduler.check_for_team_changes(st.session_state.current_time)
                    st.rerun()
            with col3:
                if st.button("Assign Flights"):
                    scheduler.assign_flights_in_window(st.session_state.current_time, window_hours=4)
                    st.rerun()
            
            # Metrics
            summary = scheduler.get_schedule_summary()
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Flights", summary['total_flights'])
            col2.metric("Assigned Flights", summary['assigned_flights'])
            col3.metric("Pending Notifications", scheduler.notification_system.get_notification_count())
            col4.metric("Active Teams", len(scheduler.team_manager.teams))
        
        with tab2:
            st.header("Flight Schedule with Team Assignments")
            
            if scheduler.assignments:
                flight_data = []
                for assignment in scheduler.assignments:
                    eta_str = assignment['eta'].strftime('%H:%M') if hasattr(assignment['eta'], 'strftime') else 'N/A'
                    etd_str = assignment['etd'].strftime('%H:%M') if hasattr(assignment['etd'], 'strftime') else 'N/A'
                    
                    flight_data.append({
                        'Arrival Flight #': assignment['flight_id'],
                        'Departure Flight #': assignment.get('outbound_flight', 'N/A'),
                        'Gate': assignment['gate'],
                        'ETA': eta_str,
                        'ETD': etd_str,
                        'Inbound City': assignment['inbound_city'],
                        'Outbound City': assignment['outbound_city'],
                        'Heaviness': assignment['heaviness'],
                        'Ramp Team': assignment['team_assigned'] if assignment['team_assigned'] else 'UNASSIGNED',
                        'Status': '✅ Assigned' if assignment['assignment_success'] else '❌ Unassigned'
                    })
                
                flight_df = pd.DataFrame(flight_data)
                st.dataframe(flight_df, use_container_width=True, hide_index=True)
                
                # Show team member details for each flight
                st.divider()
                st.subheader("Team Details by Flight")
                
                for assignment in scheduler.assignments:
                    if assignment['assignment_success'] and assignment['team_assigned']:
                        with st.expander(f"Flight {assignment['flight_id']} - Team {assignment['team_assigned']} - {assignment['inbound_city']}→{assignment['outbound_city']}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**Gate:** {assignment['gate']}")
                                st.write(f"**Time:** {assignment['eta'].strftime('%H:%M')} - {assignment['etd'].strftime('%H:%M')}")
                            with col2:
                                st.write(f"**Heaviness:** {assignment['heaviness']}")
                                st.write(f"**Aircraft:** {assignment.get('aircraft', 'N/A')}")
                            
                            st.write("**Team Members:**")
                            for member in assignment['team_members']:
                                st.write(f"• {flip_name(member)}")
                
                if st.button("Export Schedule"):
                    scheduler.export_schedule()
                    st.success("Schedule exported!")
            else:
                st.info("No flights assigned yet. Click 'Assign Flights' in the Dashboard tab to begin.")
                
                # Show unassigned flights
                st.subheader("Unassigned Flights")
                flights_df = scheduler.flight_handler.flights_df
                
                flight_table_data = []
                for _, flight in flights_df.iterrows():
                    flight_table_data.append({
                        'Arrival Flight #': flight['flight_number'],
                        'Departure Flight #': flight.get('outbound_flight', 'N/A'),
                        'Gate': flight.get('gate', 'N/A'),
                        'ETA': flight['eta_datetime'].strftime('%H:%M') if hasattr(flight['eta_datetime'], 'strftime') else str(flight.get('eta', 'N/A')),
                        'ETD': flight['etd_datetime'].strftime('%H:%M') if hasattr(flight['etd_datetime'], 'strftime') else str(flight.get('etd', 'N/A')),
                        'Inbound City': flight.get('city', 'N/A'),
                        'Outbound City': flight.get('outbound_city', 'N/A'),
                        'Heaviness': flight.get('heaviness', 'Medium')
                    })
                
                flight_table_df = pd.DataFrame(flight_table_data)
                st.dataframe(flight_table_df, use_container_width=True, hide_index=True)
        
        with tab3:
            st.header("Team Status")
            
            for team_name, team_data in scheduler.team_manager.teams.items():
                with st.expander(f"Team {team_name} - {team_data['size']} members - {team_data['flight_count']} flights"):
                    st.write("**Members:**")
                    for member_name in team_data['member_names']:
                        st.write(f"- {flip_name(member_name)}")
                    
                    st.write(f"**Status:** {team_data.get('current_status', 'Available')}")
                    st.write(f"**Flights Completed:** {team_data['flight_count']}")
        
        with tab4:
            st.header("Notification Center")
            
            pending = scheduler.get_pending_notifications()
            
            if not pending:
                st.success("No pending notifications")
            else:
                st.write(f"**{len(pending)} pending notification(s)**")
                
                for notification in pending:
                    formatted = scheduler.notification_system.format_notification(notification)
                    
                    with st.container():
                        st.markdown(f"### {formatted['title']}")
                        st.write(f"**Time:** {formatted['time']}")
                        st.info(formatted['message'])
                        
                        # Show details
                        cols = st.columns(2)
                        for idx, (key, value) in enumerate(formatted['details'].items()):
                            with cols[idx % 2]:
                                st.write(f"**{key}:** {value}")
                        
                        # Approval actions
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        # Manual team selection for new employees
                        manual_team = None
                        if formatted.get('allow_manual_selection'):
                            with col1:
                                manual_team = st.selectbox(
                                    "Assign to Team:",
                                    list(scheduler.team_manager.teams.keys()),
                                    key=f"team_select_{notification['id']}"
                                )
                        
                        with col2:
                            if st.button("✅ Approve", key=f"approve_{notification['id']}"):
                                success, msg = scheduler.approve_team_change(
                                    notification['id'],
                                    manual_team_assignment=manual_team
                                )
                                if success:
                                    st.success("Approved!")
                                    st.rerun()
                                else:
                                    st.error(msg)
                        
                        with col3:
                            if st.button("❌ Reject", key=f"reject_{notification['id']}"):
                                scheduler.notification_system.reject_notification(notification['id'])
                                st.warning("Rejected")
                                st.rerun()
                        
                        st.divider()

# Footer
st.markdown("---")
st.markdown("*United Ground Express Team-Based Flight Scheduler*")

if __name__ == "__main__":
    st.write("Run with: streamlit run dashboard.py")