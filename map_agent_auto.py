import folium
import streamlit as st
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic
from sql_langchain_agent import SQLLangChainAgent
import time
import requests
import polyline

# Initialize SQL Agent
@st.cache_resource
def get_sql_agent():
    return SQLLangChainAgent()

sql_agent = get_sql_agent()

# Get all stores with coordinates using LangChain agent
def get_stores_with_location():
    # Use LangChain agent to get store data
    response = sql_agent.ask_db("Get all medical stores with their store_id, store_name, address, latitude, longitude, and phone_number in a structured format")
    
    # For now, return sample data since we need structured output
    # In production, you'd parse the LangChain response or use structured output
    sample_stores = [
        {
            'store_id': 1,
            'store_name': 'MedPlus Regency Orion Baner Street',
            'address': 'Shop No.15 Ground, Regency Orion, Soc, Mohan Nagar Co-Op Society, Baner, Pune',
            'latitude': 18.5516660,
            'longitude': 73.7688460,
            'phone_number': '9226011653'
        },
        {
            'store_id': 2,
            'store_name': 'MedPlus Baner Rd Baner',
            'address': 'Milkat No.O/A/01, Green Hills Apartment, Shop No.2, Baner Rd, opp. Pantaloons',
            'latitude': 18.5580910,
            'longitude': 73.7934390,
            'phone_number': '4067006700'
        }
    ]
    return sample_stores

# Calculate distance between two points
def calculate_distance(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).kilometers

# Get route and travel time using OSRM
def get_route_info(user_lat, user_lon, store_lat, store_lon, mode="driving"):
    try:
        osrm_url = f"http://router.project-osrm.org/route/v1/{mode}/{user_lon},{user_lat};{store_lon},{store_lat}?overview=full"
        response = requests.get(osrm_url, timeout=10)
        data = response.json()
        
        if "routes" in data and len(data["routes"]) > 0:
            route = data["routes"][0]
            duration_seconds = route["duration"]
            distance_meters = route["distance"]
            geometry = route["geometry"]
            
            # Convert to readable format
            duration_minutes = int(duration_seconds / 60)
            distance_km = round(distance_meters / 1000, 2)
            route_points = polyline.decode(geometry)
            
            return {
                "duration_minutes": duration_minutes,
                "distance_km": distance_km,
                "route_points": route_points,
                "success": True
            }
    except:
        pass
    
    return {"success": False}

# Find nearest stores to user location
def find_nearest_stores(user_lat, user_lon, limit=5):
    stores = get_stores_with_location()
    
    # Add distance to each store
    for store in stores:
        distance = calculate_distance(user_lat, user_lon, float(store['latitude']), float(store['longitude']))
        store['distance_km'] = round(distance, 2)
    
    # Sort by distance and return top results
    stores.sort(key=lambda x: x['distance_km'])
    return stores[:limit]

# Create interactive map
def create_map(user_lat, user_lon, stores=None, zoom=12, show_routes=False):
    # Create base map centered on user location
    m = folium.Map(location=[user_lat, user_lon], zoom_start=zoom)
    
    # Add user location marker
    folium.Marker(
        [user_lat, user_lon],
        popup="Your Location",
        tooltip="You are here",
        icon=folium.Icon(color='red', icon='user')
    ).add_to(m)
    
    # Add store markers
    if stores is None:
        stores = get_stores_with_location()
    
    colors = ['green', 'blue', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue']
    
    for i, store in enumerate(stores):
        store_lat = float(store['latitude'])
        store_lon = float(store['longitude'])
        
        # Get route info if requested
        route_info = ""
        if show_routes and i < 3:  # Show routes for top 3 nearest stores
            route_data = get_route_info(user_lat, user_lon, store_lat, store_lon)
            if route_data["success"]:
                route_info = f"<br>🚗 {route_data['duration_minutes']} min ({route_data['distance_km']} km)"
                # Add route line
                folium.PolyLine(
                    route_data["route_points"],
                    weight=4,
                    color=colors[i % len(colors)],
                    opacity=0.8,
                    tooltip=f"Route to {store['store_name']}"
                ).add_to(m)
        
        # Create popup content
        popup_content = f"""
        <b>{store['store_name']}</b><br>
        📍 {store['address']}<br>
        📞 {store['phone_number']}<br>
        """
        
        if 'distance_km' in store:
            popup_content += f"📏 {store['distance_km']} km away"
        
        popup_content += route_info
        
        # Add store marker
        folium.Marker(
            [store_lat, store_lon],
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=store['store_name'],
            icon=folium.Icon(color=colors[i % len(colors)], icon='plus')
        ).add_to(m)
    
    return m

# Streamlit app for map functionality
def main():
    st.set_page_config(page_title="Medical Store Map", page_icon="🗺️", layout="wide")
    st.title("🗺️ Medical Store Locator with Auto Location")
    
    # Initialize session state for location
    if 'user_location' not in st.session_state:
        st.session_state.user_location = None
    
    # Location detection section
    st.header("📍 Location Detection")
    
    # Get live GPS location
    loc = get_geolocation()
    
    if loc is None:
        st.info("📍 Waiting for GPS… Please allow location access in your browser.")
        # Manual location input (fallback)
        st.subheader("Manual Location Entry")
        manual_lat = st.number_input("Latitude", value=18.5581, format="%.6f")
        manual_lon = st.number_input("Longitude", value=73.7934, format="%.6f")
        if st.button("Use Manual Location"):
            st.session_state.user_location = {'latitude': manual_lat, 'longitude': manual_lon}
            st.success("Manual location set!")
    else:
        st.success(f"Your Location: {loc['coords']['latitude']}, {loc['coords']['longitude']}")
        st.session_state.user_location = {
            'latitude': loc['coords']['latitude'], 
            'longitude': loc['coords']['longitude']
        }
    
    # Show map if location is available
    if st.session_state.user_location:
        user_lat = st.session_state.user_location['latitude']
        user_lon = st.session_state.user_location['longitude']
        
        st.success(f"📍 Your location: {user_lat:.4f}, {user_lon:.4f}")
        
        # Map options
        st.sidebar.header("🗺️ Map Options")
        show_all = st.sidebar.checkbox("Show all stores", value=True)
        show_routes = st.sidebar.checkbox("Show routes to nearest stores", value=True)
        nearest_count = st.sidebar.slider("Show nearest stores", 1, 10, 5, key="nearest_slider")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.header("Interactive Map")
            
            if show_all:
                # Show all stores
                stores = get_stores_with_location()
                # Add distances for display
                for store in stores:
                    distance = calculate_distance(user_lat, user_lon, float(store['latitude']), float(store['longitude']))
                    store['distance_km'] = round(distance, 2)
                stores.sort(key=lambda x: x['distance_km'])  # Sort by distance
                map_obj = create_map(user_lat, user_lon, stores, show_routes=show_routes)
            else:
                # Show only nearest stores
                nearest_stores = find_nearest_stores(user_lat, user_lon, nearest_count)
                map_obj = create_map(user_lat, user_lon, nearest_stores, show_routes=show_routes)
            
            # Display map
            st_folium(map_obj, width=700, height=500, key=f"map_{nearest_count}_{show_all}_{show_routes}")
        
        with col2:
            st.header("Nearest Stores")
            nearest_stores = find_nearest_stores(user_lat, user_lon, nearest_count)
            
            for i, store in enumerate(nearest_stores, 1):
                # Get route info for travel time
                route_data = get_route_info(user_lat, user_lon, float(store['latitude']), float(store['longitude']))
                travel_info = ""
                if route_data["success"]:
                    travel_info = f" • 🚗 {route_data['duration_minutes']} min"
                
                with st.expander(f"{i}. {store['store_name']} ({store['distance_km']} km{travel_info})"):
                    st.write(f"📍 **Address:** {store['address']}")
                    st.write(f"📞 **Phone:** {store['phone_number']}")
                    st.write(f"📏 **Distance:** {store['distance_km']} km")
                    if route_data["success"]:
                        st.write(f"🚗 **Travel Time:** {route_data['duration_minutes']} minutes")
                        st.write(f"🛣️ **Route Distance:** {route_data['distance_km']} km")
        
        # Quick actions
        st.header("🚀 Quick Actions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🎯 Find Nearest Store"):
                nearest = find_nearest_stores(user_lat, user_lon, 1)[0]
                st.success(f"Nearest: {nearest['store_name']} ({nearest['distance_km']} km)")
        
        with col2:
            if st.button("📊 Show All Distances"):
                stores = get_stores_with_location()
                for store in stores:
                    distance = calculate_distance(user_lat, user_lon, float(store['latitude']), float(store['longitude']))
                    st.write(f"{store['store_name']}: {distance:.2f} km")
        
        with col3:
            if st.button("🔄 Refresh Location"):
                st.session_state.user_location = None
                st.rerun()
    
    else:
        st.info("👆 Click 'Get My Location' to automatically detect your location, or use manual entry.")

if __name__ == "__main__":
    main()
