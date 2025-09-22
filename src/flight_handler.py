import pandas as pd
from datetime import datetime, timedelta
import numpy as np

class FlightHandler:
    def __init__(self):
        self.flights_df = None
        
    def load_flights(self, file_path="flights.csv"):
        """Load flight data from your CSV file"""
        try:
            # Load the CSV
            self.flights_df = pd.read_csv(file_path)
            
            # Handle your specific column names based on the flight log image
            column_mapping = {
                'FLT#': 'flight_number',
                'CTY': 'city', 
                'ETA': 'eta',
                'OO': 'outbound_operator',
                'A/CH': 'aircraft',
                'FLT#.1': 'outbound_flight',  # Second FLT# column
                'CTY.1': 'outbound_city',     # Second CTY column  
                'ETD': 'etd',
                'MST': 'mst_time',
                'GATE': 'gate'
            }
            
            # Rename columns if they exist
            for old_col, new_col in column_mapping.items():
                if old_col in self.flights_df.columns:
                    self.flights_df = self.flights_df.rename(columns={old_col: new_col})
            
            # Convert times to datetime if they're in time format
            # Assuming date is 2025-09-13 based on your employee data
            base_date = "2025-09-13"
            
            if 'eta' in self.flights_df.columns:
                # Handle time format like "5:50", "9:00", "11:29"
                self.flights_df['eta_datetime'] = pd.to_datetime(
                    base_date + ' ' + self.flights_df['eta'].astype(str), 
                    errors='coerce'
                )
            
            if 'etd' in self.flights_df.columns:
                self.flights_df['etd_datetime'] = pd.to_datetime(
                    base_date + ' ' + self.flights_df['etd'].astype(str), 
                    errors='coerce'
                )
            
            # Calculate turnaround time (for determining heaviness)
            if 'eta_datetime' in self.flights_df.columns and 'etd_datetime' in self.flights_df.columns:
                self.flights_df['turnaround_minutes'] = (
                    self.flights_df['etd_datetime'] - self.flights_df['eta_datetime']
                ).dt.total_seconds() / 60
            
            # Determine flight heaviness based on turnaround time
            self.add_flight_heaviness()
            
            print("✓ Flight data loaded successfully!")
            print(f"  Total flights: {len(self.flights_df)}")
            print(f"  Columns found: {list(self.flights_df.columns)}")
            
            # Show time range
            if 'eta_datetime' in self.flights_df.columns:
                print(f"  Time range: {self.flights_df['eta_datetime'].min().strftime('%H:%M')} to {self.flights_df['eta_datetime'].max().strftime('%H:%M')}")
            
            return True
            
        except FileNotFoundError:
            print(f"❌ File '{file_path}' not found!")
            print("Please make sure your flights.csv is in the correct location.")
            return False
        except Exception as e:
            print(f"❌ Error loading flight data: {e}")
            print("Data preview:")
            try:
                preview_df = pd.read_csv(file_path)
                print(preview_df.head())
                print(f"Columns: {list(preview_df.columns)}")
            except:
                pass
            return False
    
    def add_flight_heaviness(self):
        """Determine flight heaviness - supports both manual and automatic methods"""
        if self.flights_df is None:
            return
        
        # Check if heaviness is already provided in the CSV
        if 'heaviness' in self.flights_df.columns:
            print("✓ Using manual heaviness from CSV data")
            # Fill any missing values with Medium as default
            self.flights_df['heaviness'] = self.flights_df['heaviness'].fillna('Medium')
            return
        
        # If no manual heaviness, use automatic estimation as fallback
        print("ℹ No manual heaviness found, using automatic estimation")
        self.flights_df['heaviness'] = 'Medium'  # Default
        
        if 'turnaround_minutes' in self.flights_df.columns:
            # Classify based on turnaround time (as backup method)
            conditions = [
                self.flights_df['turnaround_minutes'] == 60,   # Quick turnaround = Heavy
                self.flights_df['turnaround_minutes'] == 60,   # Normal turnaround = Medium
                self.flights_df['turnaround_minutes'] == 60     # Long turnaround = Light
            ]
            choices = ['Heavy', 'Medium', 'Light']
            self.flights_df['heaviness'] = np.select(conditions, choices, default='Medium')
    
    def set_manual_heaviness_by_city(self, city_heaviness_map):
        """
        Set heaviness based on city routes
        
        Example usage:
        city_map = {
            'DEN': 'Heavy',    # Denver flights are heavy
            'CHI': 'Light',    # Chicago flights are light  
            'ORD': 'Light',    # Chicago O'Hare
            'MDW': 'Light',    # Chicago Midway
            'LAX': 'Heavy',    # Los Angeles heavy
            'SEA': 'Medium'    # Seattle medium
        }
        """
        if self.flights_df is None:
            print("❌ No flight data loaded!")
            return
        
        # Apply to inbound city
        for city, heaviness in city_heaviness_map.items():
            if 'city' in self.flights_df.columns:
                mask = self.flights_df['city'] == city
                self.flights_df.loc[mask, 'heaviness'] = heaviness
                
            # Also apply to outbound city
            if 'outbound_city' in self.flights_df.columns:
                mask = self.flights_df['outbound_city'] == city
                self.flights_df.loc[mask, 'heaviness'] = heaviness
        
        print(f"✓ Manual heaviness applied for {len(city_heaviness_map)} cities")
    
    def set_manual_heaviness_by_flight(self, flight_heaviness_map):
        """
        Set heaviness for specific flight numbers
        
        Example usage:
        flight_map = {
            400: 'Heavy',     # Flight 400 is always heavy
            2854: 'Light',    # Flight 2854 is always light
            1428: 'Medium'    # Flight 1428 is medium
        }
        """
        if self.flights_df is None:
            print("❌ No flight data loaded!")
            return
        
        for flight_num, heaviness in flight_heaviness_map.items():
            if 'flight_number' in self.flights_df.columns:
                mask = self.flights_df['flight_number'] == flight_num
                self.flights_df.loc[mask, 'heaviness'] = heaviness
                
            # Also check outbound flights
            if 'outbound_flight' in self.flights_df.columns:
                mask = self.flights_df['outbound_flight'] == flight_num
                self.flights_df.loc[mask, 'heaviness'] = heaviness
        
        print(f"✓ Manual heaviness applied for {len(flight_heaviness_map)} specific flights")
    
    def set_manual_heaviness_by_aircraft(self, aircraft_heaviness_map):
        """
        Set heaviness based on aircraft type
        
        Example usage:
        aircraft_map = {
            '37E': 'Heavy',   # Boeing 737-800 is heavy
            '73G': 'Heavy',   # Boeing 737-700 is heavy  
            'E7W': 'Light',   # Embraer 175 is light
            'E75': 'Light'    # Embraer 175 is light
        }
        """
        if self.flights_df is None:
            print("❌ No flight data loaded!")
            return
        
        for aircraft, heaviness in aircraft_heaviness_map.items():
            if 'aircraft' in self.flights_df.columns:
                mask = self.flights_df['aircraft'] == aircraft
                self.flights_df.loc[mask, 'heaviness'] = heaviness
        
        print(f"✓ Manual heaviness applied for {len(aircraft_heaviness_map)} aircraft types")
    
    def get_team_size_needed(self, heaviness):
        """Determine team size needed based on flight heaviness"""
        team_size_map = {
            'Light': 3,
            'Medium': 4, 
            'Heavy': 5
        }
        return team_size_map.get(heaviness, 4)
    
    def show_flight_summary(self):
        """Display summary of flight data"""
        if self.flights_df is None:
            print("❌ No flight data loaded!")
            return
        
        print("\n" + "="*60)
        print("FLIGHT DATA SUMMARY")
        print("="*60)
        
        print(f"Total Flights: {len(self.flights_df)}")
        
        if 'heaviness' in self.flights_df.columns:
            heaviness_counts = self.flights_df['heaviness'].value_counts()
            print(f"\nFlight Heaviness Distribution:")
            for heaviness, count in heaviness_counts.items():
                team_size = self.get_team_size_needed(heaviness)
                print(f"  {heaviness}: {count} flights ({team_size} person teams)")
        
        if 'turnaround_minutes' in self.flights_df.columns:
            print(f"\nTurnaround Times:")
            print(f"  Average: {self.flights_df['turnaround_minutes'].mean():.1f} minutes")
            print(f"  Range: {self.flights_df['turnaround_minutes'].min():.0f} - {self.flights_df['turnaround_minutes'].max():.0f} minutes")
        
        # Show sample data
        print(f"\nSample Flight Records:")
        display_cols = ['flight_number', 'city', 'eta', 'outbound_flight', 'outbound_city', 'etd', 'gate', 'heaviness']
        available_cols = [col for col in display_cols if col in self.flights_df.columns]
        print(self.flights_df[available_cols].head().to_string(index=False))
    
    def show_heaviness_summary(self):
        """Show breakdown of heaviness assignments"""
        if self.flights_df is None or 'heaviness' not in self.flights_df.columns:
            print("❌ No heaviness data available!")
            return
        
        print(f"\nHEAVINESS BREAKDOWN:")
        heaviness_counts = self.flights_df['heaviness'].value_counts()
        total_flights = len(self.flights_df)
        
        for heaviness, count in heaviness_counts.items():
            team_size = self.get_team_size_needed(heaviness)
            total_people = count * team_size
            print(f"  {heaviness}: {count} flights ({count/total_flights*100:.1f}%) - {team_size} person teams = {total_people} total positions")
        
        total_positions = sum(heaviness_counts[h] * self.get_team_size_needed(h) for h in heaviness_counts.index)
        print(f"  TOTAL: {total_positions} team positions needed across all flights")
    
    def set_flight_date(self, date_str="2025-09-13"):
        """Update the base date for all flight times"""
        if self.flights_df is None:
            print("❌ No flight data loaded!")
            return
        
        if 'eta' in self.flights_df.columns:
            self.flights_df['eta_datetime'] = pd.to_datetime(
                date_str + ' ' + self.flights_df['eta'].astype(str), 
                errors='coerce'
            )
        
        if 'etd' in self.flights_df.columns:
            self.flights_df['etd_datetime'] = pd.to_datetime(
                date_str + ' ' + self.flights_df['etd'].astype(str), 
                errors='coerce'
            )
        
        # Recalculate turnaround times and heaviness
        if 'eta_datetime' in self.flights_df.columns and 'etd_datetime' in self.flights_df.columns:
            self.flights_df['turnaround_minutes'] = (
                self.flights_df['etd_datetime'] - self.flights_df['eta_datetime']
            ).dt.total_seconds() / 60
            self.add_flight_heaviness()
        
        print(f"✓ Flight date updated to {date_str}")

# Create sample data based on your flight log image
def create_sample_flight_data():
    """Create sample data based on your flight log image"""
    sample_flights = {
        'flight_number': [400, 2854, 1428, 2046, 2141, 2336, 605, 554],
        'city': ['SEA', 'SFO', 'EWR', 'ORD', 'IAH', 'IAD', 'DEN', 'EWR'], 
        'eta': ['5:50', '5:28', '8:05', '9:00', '9:28', '9:24', '11:29', '11:36'],
        'outbound_operator': ['UA', 'UA', 'UA', 'AS', 'UA', 'UA', 'UA', 'UA'],
        'aircraft': ['37E', '73G', '37E', '', '19F', '20S', '19G', '19G'],
        'outbound_flight': [7275, 1215, 7342, 383, 3720, 1540, 8830, 4274],
        'outbound_city': ['IAH', 'ORD', 'DEN', 'SEA', 'ORD', 'IAH', 'IAD', 'SFO'],
        'etd': ['6:00', '6:05', '7:00', '7:10', '8:00', '8:05', '8:15', '8:40'],
        'mst_time': [51, 34, 51, '', 43, 34, 34, 52],
        'gate': ['A4', 'A3', 'A7', 'B9', 'A4', 'A3', 'A7', 'A8']
    }
    
    df = pd.DataFrame(sample_flights)
    return df

if __name__ == "__main__":
    print("FlightHandler class ready!")
    print("To use: import this file and create FlightHandler()")
    print("Then call flight_handler.load_flights('your_file.csv')")