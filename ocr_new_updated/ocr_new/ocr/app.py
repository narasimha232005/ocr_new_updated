import streamlit as st
import io
import pandas as pd
import folium
from streamlit_folium import folium_static
from PIL import Image
import google.generativeai as genai
import overpy
from geopy.distance import geodesic
import base64
from datetime import datetime
import random

# Gemini API Key
GEMINI_API_KEY = "AIzaSyBQXPfWI6etj89lYogiBgL2mokBudO2zV0"  # Replace with your Gemini API key
genai.configure(api_key=GEMINI_API_KEY)

# Initialize the Gemini model
model = genai.GenerativeModel('gemini-2.0-flash')

# Default locations for Guntur, Hyderabad, and New Delhi
DEFAULT_LOCATIONS = {
    "Guntur": (16.3067, 80.4365),
    "Hyderabad": (17.3850, 78.4867),
    "New Delhi": (28.6139, 77.2090),
}

# Background images for different pages
BACKGROUND_IMAGES = {
    "home": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80",
    "prescription": "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80",
    "pharmacy": "https://images.unsplash.com/photo-1631549916768-4119b4220142?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2069&q=80",
    "health_tips": "https://images.unsplash.com/photo-1511688878353-3a2f5be94cd7?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1974&q=80",
    "medicine_reminder": "https://images.unsplash.com/photo-1471864190281-a93a3070b6de?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80",
    "emergency": "https://images.unsplash.com/photo-1503508343067-c4103b7140b3?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80"
}

# Function to set background image
def set_background(image_url):
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("{image_url}");
            background-size: cover;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        .main .block-container {{
            background-color: rgba(255, 255, 255, 0.85);
            padding: 2rem;
            border-radius: 10px;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
        }}
        .stButton>button {{
            background-color: #3498db;
            color: white;
            border-radius: 5px;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: bold;
        }}
        .stButton>button:hover {{
            background-color: #2980b9;
        }}
        .css-1aumxhk {{
            background-color: rgba(255, 255, 255, 0.85);
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# Function to extract text from an image using Gemini Pro Vision.
def extract_text_from_image(image):
    """Extract text from an image using Gemini Pro Vision."""
    try:
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        # Create the content part properly according to Gemini API
        image_part = {"mime_type": "image/png", "data": img_byte_arr}
        
        # Create the prompt
        prompt = "Extract and provide all the text from this image."
        
        # Generate content using the proper approach
        response = model.generate_content(
            contents=[{"role": "user", "parts": [prompt, image_part]}]
        )
        
        # Properly access the response text
        if response and hasattr(response, 'text'):
            return response.text
        else:
            return "No text extracted from image."

    except Exception as e:
        st.error(f"Gemini Pro Vision Error: {str(e)}")
        return ""

# Function to find nearby pharmacies using Overpass API
def find_nearby_pharmacies(latitude, longitude, max_distance=20):
    """
    Find pharmacies within a specified distance from a given location using Overpass API.
    """
    try:
        # Initialize Overpass API
        api = overpy.Overpass()
        
        # Construct Overpass query to find pharmacies
        query = f"""
        [out:json];
        (
            node["amenity"="pharmacy"](around:{max_distance * 1000},{latitude},{longitude});
            way["amenity"="pharmacy"](around:{max_distance * 1000},{latitude},{longitude});
            relation["amenity"="pharmacy"](around:{max_distance * 1000},{latitude},{longitude});
        );
        out center;
        """
        
        # Execute the query
        result = api.query(query)
        
        # Store nearby pharmacies
        nearby_pharmacies = []
        
        # Process pharmacies
        for pharmacy in result.nodes + result.ways + result.relations:
            # Get pharmacy location
            if hasattr(pharmacy, 'center_lat') and hasattr(pharmacy, 'center_lon'):
                pharmacy_lat = pharmacy.center_lat
                pharmacy_lon = pharmacy.center_lon
            else:
                pharmacy_lat = pharmacy.lat
                pharmacy_lon = pharmacy.lon
            
            # Calculate distance
            distance = geodesic((latitude, longitude), (pharmacy_lat, pharmacy_lon)).kilometers
            
            # Prepare pharmacy details
            pharmacy_info = {
                'name': pharmacy.tags.get('name', 'Unnamed Pharmacy'),
                'address': pharmacy.tags.get('addr:full', pharmacy.tags.get('addr:street', 'No address')),
                'phone': pharmacy.tags.get('phone', 'N/A'),
                'opening_hours': pharmacy.tags.get('opening_hours', 'N/A'),
                'latitude': pharmacy_lat,
                'longitude': pharmacy_lon,
                'distance': round(distance, 2)
            }
            
            nearby_pharmacies.append(pharmacy_info)
        
        # Sort pharmacies by distance
        nearby_pharmacies.sort(key=lambda x: x['distance'])
        
        return nearby_pharmacies
    
    except Exception as e:
        st.error(f"Error finding pharmacies: {str(e)}")
        return []

# Function to create an interactive map with pharmacy markers
def create_map(latitude, longitude, pharmacies):
    """Create an interactive map with pharmacy markers."""
    m = folium.Map(location=[latitude, longitude], zoom_start=12)
    folium.Marker(
        [latitude, longitude],
        popup="Your Location",
        icon=folium.Icon(color="red", icon="home"),
    ).add_to(m)

    for pharmacy in pharmacies:
        folium.Marker(
            [pharmacy["latitude"], pharmacy["longitude"]],
            popup=f"<b>{pharmacy['name']}</b><br>Address: {pharmacy['address']}<br>Phone: {pharmacy['phone']}<br>Hours: {pharmacy['opening_hours']}<br>Distance: {pharmacy['distance']} km",
            icon=folium.Icon(color="blue", icon="plus"),
        ).add_to(m)

    return m

# Function to generate herbal remedy suggestions using Gemini API
def suggest_herbal_remedies(text):
    """Generate herbal remedy suggestions using Gemini API."""
    try:
        # Define the prompt for Gemini
        prompt = f"""
        You are a professional medical assistant specializing in herbal remedies.
        Analyze the following prescription text and provide herbal remedy suggestions:

        {text}

        Provide a structured response with:
        - Suggested herbal remedies
        - Dosage recommendations
        - Precautions (if any)
        """
        
        # Generate response using Gemini
        response = model.generate_content(
            contents=[{"role": "user", "parts": [prompt]}]
        )
        
        if response and hasattr(response, 'text'):
            return response.text
        else:
            return "No suggestions generated."
            
    except Exception as e:
        st.error(f"Gemini API Error: {str(e)}")
        return "Failed to generate suggestions. Please try again."

# Function to generate health tips based on symptoms
def generate_health_tips(symptoms):
    """Generate health tips based on symptoms using Gemini API."""
    try:
        prompt = f"""
        You are a healthcare expert. Based on the following symptoms, provide helpful health tips and recommendations:

        Symptoms: {symptoms}

        Provide a structured response with:
        1. Possible causes (non-diagnostic)
        2. Home remedies and lifestyle recommendations
        3. When to seek professional medical help
        """
        
        response = model.generate_content(
            contents=[{"role": "user", "parts": [prompt]}]
        )
        
        if response and hasattr(response, 'text'):
            return response.text
        else:
            return "No health tips generated."
            
    except Exception as e:
        st.error(f"Gemini API Error: {str(e)}")
        return "Failed to generate health tips. Please try again."

# Function to find emergency services
def find_emergency_services(latitude, longitude, service_type="hospital", max_distance=20):
    """Find emergency services near a location."""
    try:
        # Initialize Overpass API
        api = overpy.Overpass()
        
        # Construct Overpass query
        query = f"""
        [out:json];
        (
            node["amenity"="{service_type}"](around:{max_distance * 1000},{latitude},{longitude});
            way["amenity"="{service_type}"](around:{max_distance * 1000},{latitude},{longitude});
            relation["amenity"="{service_type}"](around:{max_distance * 1000},{latitude},{longitude});
        );
        out center;
        """
        
        # Execute the query
        result = api.query(query)
        
        # Store emergency services
        emergency_services = []
        
        # Process services
        for service in result.nodes + result.ways + result.relations:
            # Get service location
            if hasattr(service, 'center_lat') and hasattr(service, 'center_lon'):
                service_lat = service.center_lat
                service_lon = service.center_lon
            else:
                service_lat = service.lat
                service_lon = service.lon
            
            # Calculate distance
            distance = geodesic((latitude, longitude), (service_lat, service_lon)).kilometers
            
            # Prepare service details
            service_info = {
                'name': service.tags.get('name', f'Unnamed {service_type.capitalize()}'),
                'address': service.tags.get('addr:full', service.tags.get('addr:street', 'No address')),
                'phone': service.tags.get('phone', 'N/A'),
                'emergency': service.tags.get('emergency', 'Yes'),
                'latitude': service_lat,
                'longitude': service_lon,
                'distance': round(distance, 2)
            }
            
            emergency_services.append(service_info)
        
        # Sort services by distance
        emergency_services.sort(key=lambda x: x['distance'])
        
        return emergency_services
    
    except Exception as e:
        st.error(f"Error finding emergency services: {str(e)}")
        return []

# Home page function
def home_page():
    set_background(BACKGROUND_IMAGES["home"])
    st.title("🩺 Pharmacy & Medicine Assistant")
    
    # Welcome container with app overview
    st.markdown("""
    <div style="background-color: rgba(255, 255, 255, 0.9); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
        <h2 style="color: #3498db;">Welcome to Your Healthcare Companion</h2>
        <p>Your all-in-one solution for managing prescriptions, finding pharmacies, and accessing health information.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Features showcase
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background-color: rgba(52, 152, 219, 0.8); padding: 15px; border-radius: 10px; height: 200px; color: white;">
            <h3>📋 Prescription Analysis</h3>
            <p>Upload your prescription and get it analyzed instantly.</p>
            <p>Find herbal alternatives to prescribed medications.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div style="background-color: rgba(46, 204, 113, 0.8); padding: 15px; border-radius: 10px; height: 200px; color: white;">
            <h3>🏥 Find Pharmacies</h3>
            <p>Locate nearby pharmacies with an interactive map.</p>
            <p>Get directions and contact information.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown("""
        <div style="background-color: rgba(155, 89, 182, 0.8); padding: 15px; border-radius: 10px; height: 200px; color: white;">
            <h3>⏰ Health Management</h3>
            <p>Set medicine reminders.</p>
            <p>Access health tips and emergency services.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Quick access section
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("Quick Access")
    
    quick_col1, quick_col2, quick_col3 = st.columns(3)
    with quick_col1:
        if st.button("📋 Analyze Prescription"):
            st.session_state.page = "prescription"
            st.rerun()
    
    with quick_col2:
        if st.button("🔍 Find Pharmacies"):
            st.session_state.page = "pharmacy"
            st.rerun()
    
    with quick_col3:
        if st.button("🚑 Emergency Services"):
            st.session_state.page = "emergency"
            st.rerun()

# Prescription page function
def prescription_page():
    set_background(BACKGROUND_IMAGES["prescription"])
    st.title("📋 Prescription Analysis")
    st.write("Upload your prescription and get detailed analysis and herbal alternatives.")
    
    uploaded_file = st.file_uploader("Upload an image of your prescription", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Prescription", use_column_width=True)

        # Extract text from the image
        with st.spinner("Extracting text from image..."):
            extracted_text = extract_text_from_image(image)
            st.text_area("Extracted Text", extracted_text, height=150)

        # Herbal Remedy Suggestions
        st.subheader("💊 Herbal Remedy Suggestions")
        if st.button("Get Herbal Remedies"):
            with st.spinner("Generating herbal remedy suggestions..."):
                suggestions = suggest_herbal_remedies(extracted_text)
                st.markdown(f"""
                <div style="background-color: rgba(255, 255, 255, 0.9); padding: 20px; border-radius: 10px; margin-top: 20px;">
                    <h3 style="color: #2ecc71;">Herbal Alternatives</h3>
                    {suggestions}
                </div>
                """, unsafe_allow_html=True)

        # Save to medicine reminder option
        st.subheader("⏰ Add to Medicine Reminder")
        with st.expander("Set Medication Reminder"):
            medicine_name = st.text_input("Medicine Name")
            dosage = st.text_input("Dosage")
            frequency = st.selectbox("Frequency", ["Once daily", "Twice daily", "Three times daily", "Four times daily", "As needed"])
            start_date = st.date_input("Start Date", datetime.now())
            
            if st.button("Save Reminder"):
                if medicine_name and dosage:
                    if "reminders" not in st.session_state:
                        st.session_state.reminders = []
                    
                    reminder = {
                        "medicine": medicine_name,
                        "dosage": dosage,
                        "frequency": frequency,
                        "start_date": start_date.strftime("%Y-%m-%d")
                    }
                    
                    st.session_state.reminders.append(reminder)
                    st.success(f"Reminder set for {medicine_name}!")
                else:
                    st.error("Please enter medicine name and dosage.")

# Pharmacy locator page function
def pharmacy_page():
    set_background(BACKGROUND_IMAGES["pharmacy"])
    st.title("🔍 Pharmacy Locator")
    st.write("Find pharmacies near your location and view them on an interactive map.")
    
    # Location selection
    st.subheader("Select Your Location")
    location_tab1, location_tab2 = st.tabs(["Choose from list", "Custom location"])
    
    with location_tab1:
        location = st.selectbox("Choose a location:", list(DEFAULT_LOCATIONS.keys()))
        latitude, longitude = DEFAULT_LOCATIONS[location]
    
    with location_tab2:
        col1, col2 = st.columns(2)
        with col1:
            custom_latitude = st.number_input("Latitude", value=DEFAULT_LOCATIONS["Hyderabad"][0], format="%.4f")
        with col2:
            custom_longitude = st.number_input("Longitude", value=DEFAULT_LOCATIONS["Hyderabad"][1], format="%.4f")
        
        if st.button("Use Custom Location"):
            latitude, longitude = custom_latitude, custom_longitude
    
    # Search parameters
    st.subheader("Search Parameters")
    search_radius = st.slider("Search radius (km)", 1, 50, 20)
    
    # Filter options
    with st.expander("Advanced Filters"):
        open_now = st.checkbox("Open Now")
        has_delivery = st.checkbox("Offers Delivery")
    
    # Find pharmacies button
    if st.button("🔍 Find Nearby Pharmacies", type="primary"):
        with st.spinner("Searching for nearby pharmacies..."):
            pharmacies = find_nearby_pharmacies(latitude, longitude, search_radius)
            
            # Apply filters (these would need to be implemented in the find_nearby_pharmacies function)
            # This is just a placeholder to show the UI
            if len(pharmacies) > 0:
                if open_now:
                    # Filter logic would go here
                    pass
                if has_delivery:
                    # Filter logic would go here
                    pass
                
                # Display results
                st.success(f"Found {len(pharmacies)} pharmacies within {search_radius} km")
                
                # Show map
                st.subheader("📍 Pharmacy Locations")
                map_obj = create_map(latitude, longitude, pharmacies)
                folium_static(map_obj)
                
                # Show list
                st.subheader("📋 Pharmacy List")
                for i, pharmacy in enumerate(pharmacies[:10]):  # Show top 10
                    st.markdown(f"""
                    <div style="background-color: rgba(255, 255, 255, 0.9); padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                        <h4>{i+1}. {pharmacy['name']}</h4>
                        <p><strong>Address:</strong> {pharmacy['address']}</p>
                        <p><strong>Distance:</strong> {pharmacy['distance']} km</p>
                        <p><strong>Phone:</strong> {pharmacy['phone']}</p>
                        <p><strong>Hours:</strong> {pharmacy['opening_hours']}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning(f"No pharmacies found within {search_radius} km.")

# Health tips page function
def health_tips_page():
    set_background(BACKGROUND_IMAGES["health_tips"])
    st.title("💡 Health Tips")
    st.write("Get personalized health tips based on your symptoms or conditions.")
    
    # Common health topics
    st.subheader("Common Health Topics")
    topics = ["Common Cold", "Headache", "Digestion Issues", "Stress & Anxiety", "Sleep Problems", "Joint Pain", "Skin Issues"]
    selected_topic = st.selectbox("Select a health topic:", topics)
    
    # Custom symptoms
    st.subheader("Or describe your symptoms")
    custom_symptoms = st.text_area("Describe your symptoms or health concerns:", 
                                  placeholder="Example: I've been experiencing headaches and fatigue for the past week...")
    
    # Get tips button
    if st.button("Get Health Tips"):
        symptoms = custom_symptoms if custom_symptoms else selected_topic
        with st.spinner("Generating health tips..."):
            tips = generate_health_tips(symptoms)
            
            st.markdown(f"""
            <div style="background-color: rgba(255, 255, 255, 0.9); padding: 20px; border-radius: 10px; margin-top: 20px;">
                <h3 style="color: #3498db;">Health Tips for: {symptoms}</h3>
                {tips}
                <div style="background-color: rgba(231, 76, 60, 0.1); padding: 10px; border-radius: 5px; margin-top: 20px; border-left: 4px solid #e74c3c;">
                    <p><strong>Disclaimer:</strong> The information provided is for educational purposes only and is not a substitute for professional medical advice, diagnosis, or treatment.</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Health articles
    st.subheader("Featured Health Articles")
    article_col1, article_col2 = st.columns(2)
    
    with article_col1:
        st.markdown("""
        <div style="background-color: rgba(255, 255, 255, 0.9); padding: 15px; border-radius: 10px; height: 200px;">
            <h4>Boost Your Immunity Naturally</h4>
            <p>Discover foods and habits that strengthen your immune system.</p>
            <p style="color: #3498db;">Read more →</p>
        </div>
        """, unsafe_allow_html=True)
    
    with article_col2:
        st.markdown("""
        <div style="background-color: rgba(255, 255, 255, 0.9); padding: 15px; border-radius: 10px; height: 200px;">
            <h4>Mental Wellness Tips</h4>
            <p>Simple daily practices to maintain good mental health.</p>
            <p style="color: #3498db;">Read more →</p>
        </div>
        """, unsafe_allow_html=True)

# Medicine reminder page function
def medicine_reminder_page():
    set_background(BACKGROUND_IMAGES["medicine_reminder"])
    st.title("⏰ Medicine Reminder")
    st.write("Keep track of your medications and never miss a dose.")
    
    # Initialize reminders if not exists
    if "reminders" not in st.session_state:
        st.session_state.reminders = []
    
    # Add new reminder form
    st.subheader("Add New Reminder")
    with st.form("reminder_form"):
        col1, col2 = st.columns(2)
        with col1:
            medicine_name = st.text_input("Medicine Name")
            dosage = st.text_input("Dosage (e.g., 10mg)")
        with col2:
            frequency = st.selectbox("Frequency", ["Once daily", "Twice daily", "Three times daily", "Four times daily", "As needed"])
            time_of_day = st.multiselect("Time of Day", ["Morning", "Afternoon", "Evening", "Night"])
        
        notes = st.text_area("Notes (e.g., take with food)", max_chars=100)
        submitted = st.form_submit_button("Add Reminder")
        
        if submitted:
            if medicine_name and dosage and time_of_day:
                new_reminder = {
                    "id": random.randint(1000, 9999),
                    "medicine": medicine_name,
                    "dosage": dosage,
                    "frequency": frequency,
                    "time_of_day": time_of_day,
                    "notes": notes,
                    "added_on": datetime.now().strftime("%Y-%m-%d")
                }
                
                st.session_state.reminders.append(new_reminder)
                st.success(f"Reminder added for {medicine_name}!")
            else:
                st.error("Please fill in all required fields.")
    
    # Show existing reminders
    st.subheader("Your Medication Schedule")
    if st.session_state.reminders:
        for i, reminder in enumerate(st.session_state.reminders):
            st.markdown(f"""
            <div style="background-color: rgba(255, 255, 255, 0.9); padding: 15px; border-radius: 10px; margin-bottom: 10px; position: relative;">
                <h4>{reminder['medicine']} ({reminder['dosage']})</h4>
                <p><strong>Frequency:</strong> {reminder['frequency']}</p>
                <p><strong>Time:</strong> {", ".join(reminder.get('time_of_day', ['Not specified']))}</p>
                <p><strong>Notes:</strong> {reminder.get('notes', 'None')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 10])
            with col1:
                if st.button(f"Delete", key=f"delete_{i}"):
                    st.session_state.reminders.pop(i)
                    st.rerun()
    else:
        st.info("No medication reminders set. Add your first reminder using the form above.")
    
    # Export reminders
    if st.session_state.reminders:
        if st.button("Export Medication Schedule"):
            # In a real app, this would generate a PDF or calendar file
            st.success("Medication schedule exported successfully!")

# Emergency page function
def emergency_page():
    set_background(BACKGROUND_IMAGES["emergency"])
    st.title("🚑 Emergency Services")
    st.write("Find nearby emergency medical services quickly.")
    
    # Big emergency button
    st.markdown("""
    <div style="background-color: rgba(231, 76, 60, 0.9); padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
        <h2 style="color: white;">In case of emergency, dial your local emergency number</h2>
        <h1 style="color: white; font-size: 48px;">112 / 108</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Location selection
    st.subheader("Find Emergency Services")
    location = st.selectbox("Choose your location:", list(DEFAULT_LOCATIONS.keys()))
    latitude, longitude = DEFAULT_LOCATIONS[location]
    
    # Custom location option
    custom_location = st.checkbox("Use custom location")
    if custom_location:
        col1, col2 = st.columns(2)
        with col1:
            latitude = st.number_input("Latitude", value=latitude, format="%.4f")
        with col2:
            longitude = st.number_input("Longitude", value=longitude, format="%.4f")
    
    # Service type selection
    service_type = st.radio("Service type:", ["hospital", "clinic", "doctors"], horizontal=True)
    search_radius = st.slider("Search radius (km)", 1, 50, 20)
    
    # Find services button
    if st.button("Find Emergency Services", type="primary"):
        with st.spinner("Searching for emergency services..."):
            services = find_emergency_services(latitude, longitude, service_type, search_radius)
            
            if services:
                st.success(f"Found {len(services)} emergency services within {search_radius} km")
                
                # Show map
                st.subheader("📍 Emergency Services Locations")
                
                m = folium.Map(location=[latitude, longitude], zoom_start=12)
                folium.Marker(
                    [latitude, longitude],
                    popup="Your Location",
                    icon=folium.Icon(color="red", icon="home"),
                ).add_to(m)

                for service in services:
                    folium.Marker(
                        [service["latitude"], service["longitude"]],
                        popup=f"<b>{service['name']}</b><br>Address: {service['address']}<br>Phone: {service['phone']}<br>Distance: {service['distance']} km",
                        icon=folium.Icon(color="darkred", icon="plus"),
                    ).add_to(m)
                
                folium_static(m)
                
                # Show list
                st.subheader("📋 Emergency Services List")
                for i, service in enumerate(services[:5]):  # Show top 5
                    st.markdown(f"""
                    <div style="background-color: rgba(231, 76, 60, 0.8); padding: 15px; border-radius: 10px; margin-bottom: 10px; color: white;">
                        <h4>{i+1}. {service['name']}</h4>
                        <p><strong>Address:</strong> {service['address']}</p>
                        <p><strong>Phone:</strong> {service['phone']}</p>
                        <p><strong>Distance:</strong> {service['distance']} km</p>
                        <a href="https://www.google.com/maps/dir/?api=1&destination={service['latitude']},{service['longitude']}" target="_blank" style="color: white; text-decoration: underline;">Get Directions</a>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning(f"No emergency services found within {search_radius} km.")
    
    # First aid tips
    st.subheader("Basic First Aid Tips")
    first_aid_topics = ["CPR", "Bleeding", "Burns", "Choking", "Fractures", "Heart Attack", "Stroke"]
    selected_topic = st.selectbox("Select a first aid topic:", first_aid_topics)
    
    # Display first aid information based on selection
    if selected_topic == "CPR":
        st.markdown("""
        <div style="background-color: rgba(255, 255, 255, 0.9); padding: 20px; border-radius: 10px;">
            <h3>CPR (Cardiopulmonary Resuscitation)</h3>
            <ol>
                <li>Check if the person is responsive</li>
                <li>Call emergency services (112/108)</li>
                <li>Place the person on their back on a firm surface</li>
                <li>Place the heel of your hand on the center of the chest</li>
                <li>Place your other hand on top and interlock fingers</li>
                <li>Perform chest compressions at a rate of 100-120 per minute</li>
                <li>Press down at least 2 inches (5 cm)</li>
                <li>Allow chest to completely recoil after each compression</li>
                <li>Continue until help arrives</li>
            </ol>
            <p><strong>Note:</strong> This is basic information only. Proper CPR training is recommended.</p>
        </div>
        """, unsafe_allow_html=True)
    elif selected_topic == "Bleeding":
        st.markdown("""
        <div style="background-color: rgba(255, 255, 255, 0.9); padding: 20px; border-radius: 10px;">
            <h3>Controlling Bleeding</h3>
            <ol>
                <li>Apply direct pressure to the wound using a clean cloth or bandage</li>
                <li>If possible, elevate the injured area above the level of the heart</li>
                <li>Apply pressure for at least 15 minutes</li>
                <li>If bleeding continues, apply pressure to the arterial pressure point</li>
                <li>For severe bleeding, apply a tourniquet only as a last resort</li>
                <li>Seek medical help immediately</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
    # Add similar blocks for other first aid topics




def suggest_alternative_medicines(medicine_name):
    """Generate alternative medicine suggestions using Gemini API."""
    try:
        # Define the prompt for Gemini
        prompt = f"""
        You are a professional pharmacist. Suggest 5-7 alternative medicines for:
        
        {medicine_name}
        
        Provide the response in this structured format:
        - <Alternative Medicine 1>: <Brief description of when it might be preferred>
        - <Alternative Medicine 2>: <Brief description of when it might be preferred>
        - ...
        
        Also include any important precautions about substitutions.
        """
        
        # Generate response using Gemini
        response = model.generate_content(
            contents=[{"role": "user", "parts": [prompt]}]
        )
        
        if response and hasattr(response, 'text'):
            return response.text
        else:
            return "No alternatives found or error generating suggestions."
            
    except Exception as e:
        st.error(f"Gemini API Error: {str(e)}")
        return "Failed to generate alternatives. Please try again."
    




def prescription_page():
    set_background(BACKGROUND_IMAGES["prescription"])
    st.title("📋 Prescription Analysis")
    st.write("Upload your prescription or search for medicine alternatives.")
    
    # Create tabs for different functionalities
    tab1, tab2 = st.tabs(["Prescription Upload", "Medicine Alternatives"])
    
    with tab1:
        # Existing prescription upload functionality
        uploaded_file = st.file_uploader("Upload an image of your prescription", type=["jpg", "jpeg", "png"])
        
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Prescription", use_column_width=True)

            # Extract text from the image
            with st.spinner("Extracting text from image..."):
                extracted_text = extract_text_from_image(image)
                st.text_area("Extracted Text", extracted_text, height=150)

            # Herbal Remedy Suggestions
            st.subheader("💊 Herbal Remedy Suggestions")
            if st.button("Get Herbal Remedies"):
                with st.spinner("Generating herbal remedy suggestions..."):
                    suggestions = suggest_herbal_remedies(extracted_text)
                    st.markdown(f"""
                    <div style="background-color: rgba(255, 255, 255, 0.9); padding: 20px; border-radius: 10px; margin-top: 20px;">
                        <h3 style="color: #2ecc71;">Herbal Alternatives</h3>
                        {suggestions}
                    </div>
                    """, unsafe_allow_html=True)

    with tab2:
        # New medicine alternatives functionality
        st.subheader("💊 Find Medicine Alternatives")
        medicine_name = st.text_input("Enter the name of the medicine you're looking to replace:")
        
        if st.button("Find Alternatives"):
            if medicine_name:
                with st.spinner(f"Searching for alternatives to {medicine_name}..."):
                    alternatives = suggest_alternative_medicines(medicine_name)
                    
                    st.markdown(f"""
                    <div style="background-color: rgba(255, 255, 255, 0.9); padding: 20px; border-radius: 10px; margin-top: 20px;">
                        <h3 style="color: #3498db;">Alternative Medicines for {medicine_name}</h3>
                        {alternatives}
                        <div style="background-color: rgba(231, 76, 60, 0.1); padding: 10px; border-radius: 5px; margin-top: 20px; border-left: 4px solid #e74c3c;">
                            <p><strong>Important:</strong> Always consult with your doctor or pharmacist before switching medications.</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("Please enter a medicine name to find alternatives.")

    # Keep the existing medicine reminder section
    st.subheader("⏰ Add to Medicine Reminder")
    with st.expander("Set Medication Reminder"):
        medicine_name = st.text_input("Medicine Name")
        dosage = st.text_input("Dosage")
        frequency = st.selectbox("Frequency", ["Once daily", "Twice daily", "Three times daily", "Four times daily", "As needed"])
        start_date = st.date_input("Start Date", datetime.now())
        
        if st.button("Save Reminder"):
            if medicine_name and dosage:
                if "reminders" not in st.session_state:
                    st.session_state.reminders = []
                
                reminder = {
                    "medicine": medicine_name,
                    "dosage": dosage,
                    "frequency": frequency,
                    "start_date": start_date.strftime("%Y-%m-%d")
                }
                
                st.session_state.reminders.append(reminder)
                st.success(f"Reminder set for {medicine_name}!")
            else:
                st.error("Please enter medicine name and dosage.")
                

# Main app function
def main():
    st.set_page_config(
        page_title="Pharmacy & Medicine Assistant",
        page_icon="🩺",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    if "page" not in st.session_state:
        st.session_state.page = "home"

    # Navigation sidebar
    with st.sidebar:
        st.title("Navigation")
        
        # Profile section (placeholder)
        st.markdown("""
        <div style="background-color: rgba(52, 152, 219, 0.3); padding: 10px; border-radius: 10px; margin-bottom: 20px;">
            <h3>👤 User Profile</h3>
            <p>Welcome to your healthcare assistant!</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Navigation buttons
        if st.button("🏠 Home", key="nav_home"):
            st.session_state.page = "home"
            st.rerun()
        
        if st.button("📋 Prescription Analysis", key="nav_prescription"):
            st.session_state.page = "prescription"
            st.rerun()
            
        if st.button("🔍 Pharmacy Locator", key="nav_pharmacy"):
            st.session_state.page = "pharmacy"
            st.rerun()
            
        if st.button("💡 Health Tips", key="nav_health_tips"):
            st.session_state.page = "health_tips"
            st.rerun()
            
        if st.button("⏰ Medicine Reminder", key="nav_medicine_reminder"):
            st.session_state.page = "medicine_reminder"
            st.rerun()
            
        if st.button("🚑 Emergency Services", key="nav_emergency"):
            st.session_state.page = "emergency"
            st.rerun()
        
        # App info
        st.markdown("---")
        st.markdown("### About")
        st.markdown("Pharmacy & Medicine Assistant v1.0")
        st.markdown("© 2025 Healthcare Solutions")
    
    # Display the selected page
    if st.session_state.page == "home":
        home_page()
    elif st.session_state.page == "prescription":
        prescription_page()
    elif st.session_state.page == "pharmacy":
        pharmacy_page()
    elif st.session_state.page == "health_tips":
        health_tips_page()
    elif st.session_state.page == "medicine_reminder":
        medicine_reminder_page()
    elif st.session_state.page == "emergency":
        emergency_page()

# Run the app
if __name__ == "__main__":
    main()