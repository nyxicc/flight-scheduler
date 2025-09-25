import streamlit as st
import pandas as pd
import subprocess
import sys
import os
from datetime import datetime
import json

# Import your existing classes
try:
    from employee_handler import EmployeeHandler
    from flight_handler import FlightHandler
    from scheduler import Scheduler
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    st.stop()

# Configure page
st.set_page_config(
    page_title="Flight Team Scheduler",
    page_icon="✈️",
    layout="wide"
)

# Initialize session state
if 'scheduling_results' not in st.session_state:
    st.session_state.scheduling_results = None
if 'team_assignments' not in st.session_state:
    st.session_state.team_assignments = {}
if 'flight_notes' not in st.session_state:
    st.session_state.flight_notes = {}
if 'manual_assignments' not in st.session_state:
    st.session_state.manual_assignments = {}

def flip_name(full_name):
    """Convert 'LastName, FirstName' to 'FirstName LastName'"""
    if ', ' in full_name:
        last, first = full_name.split(', ', 1)
        return f"{first} {last}"
    return full_name

def generate_team_names(assignments):
    """Generate Alpha, Bravo, Charlie team names"""
    team_names = ['Alpha', 'Bravo', 'Charlie', 'Delta', 'Echo', 'Foxtrot', 
                  'Golf', 'Hotel', 'India', 'Juliet', 'Kilo', 'Lima', 
                  'Mike', 'November', 'Oscar', 'Papa', 'Quebec', 'Romeo',
                  'Sierra', 'Tango', 'Uniform', 'Victor', 'Whiskey', 'X-ray', 'Yankee', 'Zulu']
    
    team_mapping = {}
    team_index = 0
    
    for assignment in assignments:
        if assignment['assignment_success']:
            flight_id = assignment['flight_id']
            if flight_id not in team_mapping:
                if team_index < len(team_names):
                    team_mapping[flight_id] = team_names[team_index]
                    team_index += 1
                else:
                    team_mapping[flight_id] = f"Team-{team_index + 1}"
                    team_index += 1
    
    return team_mapping

def run_scheduling():
    """Run the scheduling algorithm"""
    try:
        # Initialize handlers
        employee_handler = EmployeeHandler()
        flight_handler = FlightHandler()
        
        # Load data
        employee_success = employee_handler.load_employees("../data/employees.csv")
        flight_success = flight_handler.load_flights("../data/flights.csv")
        
        if not employee_success or not flight_success:
            return None, "Failed to load CSV files"
        
        # Apply Nashville heaviness rules
        nashville_city_rules = {
            'DEN': 'Heavy', 'LAX': 'Heavy', 'EWR': 'Light', 'JFK': 'Heavy', 
            'LGA': 'Heavy', 'SFO': 'Medium', 'IAH': 'Medium', 'DFW': 'Medium',
            'ATL': 'Medium', 'CLT': 'Medium', 'IAD': 'Medium', 'BWI': 'Medium',
            'PHX': 'Medium', 'ORD': 'Light', 'MDW': 'Light', 'SEA': 'Heavy',
            'PDX': 'Heavy', 'MSY': 'Light', 'MEM': 'Light', 'STL': 'Light'
        }
        
        flight_handler.set_manual_heaviness_by_city(nashville_city_rules)
        
        # Run scheduler
        scheduler = Scheduler(employee_handler, flight_handler)
        success = scheduler.run_scheduling()
        
        if success:
            return scheduler, None
        else:
            return None, "Scheduling failed"
            
    except Exception as e:
        return None, f"Error: {str(e)}"

# Main dashboard
st.title("🛫 United Ground Express - Flight Team Scheduler")
st.markdown("*Nashville Operations Dashboard*")

# Sidebar for controls
st.sidebar.header("🔧 Control Panel")

# Run scheduling button
if st.sidebar.button("🚀 Run Automatic Scheduling", type="primary"):
    with st.spinner("Running scheduling algorithm..."):
        scheduler, error = run_scheduling()
        
        if scheduler:
            st.session_state.scheduling_results = scheduler
            st.session_state.team_assignments = generate_team_names(scheduler.assignments)
            st.success("✅ Scheduling completed successfully!")
        else:
            st.error(f"❌ Scheduling failed: {error}")

# Manual controls section
st.sidebar.header("✏️ Manual Controls")

# File upload for new data
st.sidebar.subheader("📁 Upload New Data")
uploaded_employees = st.sidebar.file_uploader("Upload employees.csv", type=['csv'])
uploaded_flights = st.sidebar.file_uploader("Upload flights.csv", type=['csv'])

if uploaded_employees or uploaded_flights:
    if st.sidebar.button("💾 Save Uploaded Files"):
        if uploaded_employees:
            with open("../data/employees.csv", "wb") as f:
                f.write(uploaded_employees.getbuffer())
        if uploaded_flights:
            with open("../data/flights.csv", "wb") as f:
                f.write(uploaded_flights.getbuffer())
        st.sidebar.success("Files saved successfully!")

# Main content area
if st.session_state.scheduling_results is None:
    st.info("👆 Click 'Run Automatic Scheduling' to get started")
    st.markdown("### 📋 Instructions:")
    st.markdown("""
    1. **Upload CSV files** (optional) - or use existing files in /data folder
    2. **Run Automatic Scheduling** - generates optimized team assignments  
    3. **Review Results** - see team assignments and flight schedules
    4. **Make Manual Adjustments** - add notes or modify assignments
    5. **Export Results** - download final schedules
    """)

else:
    scheduler = st.session_state.scheduling_results
    team_names = st.session_state.team_assignments
    
    # Display results in tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "👥 Team Assignments", "✈️ Flight Schedule", "✏️ Manual Controls"])
    
    with tab1:
        st.header("📊 Scheduling Overview")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        successful = scheduler.scheduling_results['successful_assignments']
        total = len(scheduler.assignments)
        failed = scheduler.scheduling_results['failed_assignments']
        positions_filled = scheduler.scheduling_results['total_positions_filled']
        
        col1.metric("✅ Flights Assigned", successful)
        col2.metric("❌ Failed Assignments", failed)  
        col3.metric("📈 Success Rate", f"{successful/total*100:.1f}%")
        col4.metric("👥 Total Positions", positions_filled)
        
        # Employee utilization
        if hasattr(scheduler, 'employee_handler'):
            workload_summary = scheduler.employee_handler.get_workload_summary()
            if workload_summary is not None:
                st.subheader("👥 Employee Utilization")
                
                # Format for display
                display_df = workload_summary.copy()
                display_df['employee_name'] = display_df['employee_name'].apply(flip_name)
                display_df['utilization_pct'] = display_df['utilization_pct'].round(1)
                
                st.dataframe(display_df[['employee_name', 'current_flights', 'max_flights', 'utilization_pct']], 
                           use_container_width=True)
    
    with tab2:
        st.header("👥 Team Assignments")
        
        # Group assignments by team
        for assignment in scheduler.assignments:
            if assignment['assignment_success']:
                flight_id = assignment['flight_id']
                team_name = team_names.get(flight_id, "Unassigned")
                
                st.subheader(f"🎯 Team {team_name}")
                
                # Flight details
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"**Flight:** {flight_id}")
                    st.write(f"**Route:** {assignment['flight_route']}")
                    st.write(f"**Time:** {assignment['eta'].strftime('%H:%M') if hasattr(assignment['eta'], 'strftime') else assignment['eta']} - {assignment['etd'].strftime('%H:%M') if hasattr(assignment['etd'], 'strftime') else assignment['etd']}")
                    st.write(f"**Gate:** {assignment['gate']}")
                
                with col2:
                    st.write(f"**Heaviness:** {assignment['heaviness']}")
                    st.write(f"**Aircraft:** {assignment['aircraft']}")
                    st.write(f"**Team Size:** {assignment['assigned_team_size']}")
                
                # Team members
                st.write("**Team Members:**")
                team_members = [flip_name(name) for name in assignment['team_names']]
                for i, member in enumerate(team_members, 1):
                    st.write(f"{i}. {member}")
                
                st.divider()
    
    with tab3:
        st.header("✈️ Flight Schedule")
        
        # Create flight schedule table
        flight_data = []
        for assignment in scheduler.assignments:
            team_name = team_names.get(assignment['flight_id'], "Unassigned") if assignment['assignment_success'] else "FAILED"
            
            flight_data.append({
                'Flight': assignment['flight_id'],
                'Route': assignment['flight_route'],
                'ETA': assignment['eta'].strftime('%H:%M') if hasattr(assignment['eta'], 'strftime') else str(assignment['eta']),
                'ETD': assignment['etd'].strftime('%H:%M') if hasattr(assignment['etd'], 'strftime') else str(assignment['etd']),
                'Gate': assignment['gate'],
                'Aircraft': assignment['aircraft'],
                'Heaviness': assignment['heaviness'],
                'Team': team_name,
                'Status': '✅' if assignment['assignment_success'] else '❌'
            })
        
        flight_df = pd.DataFrame(flight_data)
        st.dataframe(flight_df, use_container_width=True)
        
        # Export button
        if st.button("📥 Export Flight Schedule"):
            flight_df.to_csv("../flight_schedule_export.csv", index=False)
            st.success("Schedule exported to flight_schedule_export.csv")
    
    with tab4:
        st.header("✏️ Manual Controls")
        
        st.subheader("📝 Flight Notes")
        
        # Flight notes section
        for assignment in scheduler.assignments:
            if assignment['assignment_success']:
                flight_id = assignment['flight_id']
                team_name = team_names.get(flight_id, "Unassigned")
                
                with st.expander(f"Flight {flight_id} - Team {team_name}"):
                    # Notes
                    note_key = f"note_{flight_id}"
                    current_note = st.session_state.flight_notes.get(flight_id, "")
                    
                    new_note = st.text_area(
                        f"Notes for Flight {flight_id}:", 
                        value=current_note,
                        key=note_key,
                        height=100
                    )
                    
                    if st.button(f"Save Note", key=f"save_{flight_id}"):
                        st.session_state.flight_notes[flight_id] = new_note
                        st.success("Note saved!")
                    
                    # Manual team modification
                    st.write("**Current Team:**")
                    current_team = [flip_name(name) for name in assignment['team_names']]
                    st.write(", ".join(current_team))
                    
                    # Add person to team
                    add_person = st.text_input(f"Add person to team:", key=f"add_{flight_id}")
                    if st.button(f"Add Person", key=f"add_btn_{flight_id}"):
                        if add_person:
                            # This would need integration with the scheduler to actually modify teams
                            st.info(f"Would add '{add_person}' to Flight {flight_id}")
        
        # Export all notes
        if st.session_state.flight_notes:
            st.subheader("📋 Export Notes")
            notes_data = []
            for flight_id, note in st.session_state.flight_notes.items():
                team_name = team_names.get(flight_id, "Unassigned")
                notes_data.append({
                    'Flight': flight_id,
                    'Team': team_name,
                    'Notes': note
                })
            
            notes_df = pd.DataFrame(notes_data)
            st.dataframe(notes_df, use_container_width=True)
            
            if st.button("📥 Export Notes"):
                notes_df.to_csv("../flight_notes_export.csv", index=False)
                st.success("Notes exported to flight_notes_export.csv")

# Footer
st.markdown("---")
st.markdown("*United Ground Express Flight Team Scheduler Dashboard*")

if __name__ == "__main__":
    st.markdown("Run with: `streamlit run dashboard.py`")