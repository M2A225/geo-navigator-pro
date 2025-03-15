from geopy.geocoders import Nominatim
import folium
import requests
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import ipinfo
import json
from datetime import datetime

# Configuration API
IPINFO_ACCESS_TOKEN = 'c22d4767d63836'
OSRM_PROFILES = {
    'Voiture': 'driving',
    'Vélo': 'cycling',
    'Piéton': 'walking'
}

class GeoApp:
    def __init__(self, root):
        self.root = root
        self.history = []
        self.setup_ui()
        self.load_history()

    def setup_ui(self):
        """Configure l'interface utilisateur"""
        self.root.title("Geo Navigator Pro")
        self.root.geometry("800x600")

        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Section de recherche
        search_frame = ttk.LabelFrame(main_frame, text="Recherche d'itinéraire", padding=10)
        search_frame.grid(row=0, column=0, sticky='nsew', pady=5)

        ttk.Label(search_frame, text="Départ:").grid(row=0, column=0, sticky='w')
        self.entry_start = ttk.Entry(search_frame, width=40)
        self.entry_start.grid(row=1, column=0, padx=5, pady=2)
        self.entry_start.bind('<KeyRelease>', lambda e: self.autocomplete(e, 'start'))

        ttk.Label(search_frame, text="Arrivée:").grid(row=2, column=0, sticky='w')
        self.entry_end = ttk.Entry(search_frame, width=40)
        self.entry_end.grid(row=3, column=0, padx=5, pady=2)
        self.entry_end.bind('<KeyRelease>', lambda e: self.autocomplete(e, 'end'))

        self.autocomplete_listbox = tk.Listbox(search_frame, height=3)
        self.autocomplete_listbox.grid(row=4, column=0, sticky='ew', pady=2)
        self.autocomplete_listbox.bind('<<ListboxSelect>>', self.select_autocomplete)

        ttk.Label(search_frame, text="Mode de transport:").grid(row=5, column=0, sticky='w')
        self.transport_mode = ttk.Combobox(search_frame, values=list(OSRM_PROFILES.keys()), state='readonly')
        self.transport_mode.current(0)
        self.transport_mode.grid(row=6, column=0, sticky='ew', pady=2)

        ttk.Button(search_frame, 
                 text="Me localiser", 
                 command=self.geolocate).grid(row=7, column=0, pady=5)
        
        ttk.Button(search_frame,
                 text="Calculer l'itinéraire",
                 command=self.calculate_route,
                 style='Accent.TButton').grid(row=8, column=0, pady=10)

        # Section d'information
        info_frame = ttk.LabelFrame(main_frame, text="Détails de l'itinéraire", padding=10)
        info_frame.grid(row=0, column=1, sticky='nsew', padx=10)
        
        self.lbl_distance = ttk.Label(info_frame, text="Distance: -")
        self.lbl_distance.pack(anchor='w')
        
        self.lbl_duration = ttk.Label(info_frame, text="Durée: -")
        self.lbl_duration.pack(anchor='w')

        # Historique
        history_frame = ttk.LabelFrame(main_frame, text="Historique", padding=10)
        history_frame.grid(row=1, column=0, columnspan=2, sticky='nsew', pady=10)
        
        self.history_listbox = tk.Listbox(history_frame)
        self.history_listbox.pack(fill=tk.BOTH, expand=True)
        self.history_listbox.bind('<<ListboxSelect>>', self.load_history_entry)

        # Configuration du style
        style = ttk.Style()
        style.configure('Accent.TButton', foreground='white', background='#4CAF50')

        # Configuration des poids de grille
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

    def autocomplete(self, event, field):
        """Autocomplétion des adresses avec Photon API"""
        query = event.widget.get()
        if len(query) < 3:
            self.autocomplete_listbox.delete(0, tk.END)
            return

        try:
            response = requests.get(f'https://photon.komoot.io/api/?q={query}&lang=fr', timeout=5)
            results = response.json().get('features', [])[:5]
            
            self.autocomplete_listbox.delete(0, tk.END)
            for result in results:
                name = result['properties'].get('name', '')
                city = result['properties'].get('city', '')
                country = result['properties'].get('country', '')
                self.autocomplete_listbox.insert(tk.END, f"{name}, {city}, {country}")
        except Exception as e:
            print(f"Erreur autocomplétion: {str(e)}")

    def select_autocomplete(self, event):
        """Sélection d'une suggestion d'adresse"""
        selection = self.autocomplete_listbox.curselection()
        if selection:
            address = self.autocomplete_listbox.get(selection[0])
            focused_widget = self.root.focus_get()
            if focused_widget == self.entry_start:
                self.entry_start.delete(0, tk.END)
                self.entry_start.insert(0, address)
            elif focused_widget == self.entry_end:
                self.entry_end.delete(0, tk.END)
                self.entry_end.insert(0, address)

    def geolocate(self):
        """Géolocalisation automatique"""
        try:
            handler = ipinfo.getHandler(IPINFO_ACCESS_TOKEN)
            details = handler.getDetails()
            self.entry_start.delete(0, tk.END)
            self.entry_start.insert(0, f"{details.city}, {details.region}, {details.country}")
        except Exception as e:
            messagebox.showwarning("Erreur", f"Géolocalisation impossible : {str(e)}")

    def get_coordinates(self, address):
        """Convertir une adresse en coordonnées GPS"""
        try:
            geolocator = Nominatim(user_agent="geoAppPro")
            location = geolocator.geocode(address)
            return (location.latitude, location.longitude) if location else None
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de géocodage : {str(e)}")
            return None

    def calculate_route(self):
        """Calculer l'itinéraire"""
        try:
            start_address = self.entry_start.get()
            end_address = self.entry_end.get()
            profile = OSRM_PROFILES[self.transport_mode.get()]

            if not start_address or not end_address:
                messagebox.showwarning("Attention", "Veuillez saisir les deux adresses !")
                return

            start_coord = self.get_coordinates(start_address)
            end_coord = self.get_coordinates(end_address)

            if not start_coord or not end_coord:
                return

            # Correction de l'URL avec paramètre geometries
            url = f"http://router.project-osrm.org/route/v1/{profile}/{start_coord[1]},{start_coord[0]};{end_coord[1]},{end_coord[0]}?overview=full&geometries=geojson"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get('code') != 'Ok' or not data.get('routes'):
                raise ValueError("Aucun itinéraire trouvé")

            route = data['routes'][0]
            self.display_route_info(route)
            self.create_map(start_coord, end_coord, route['geometry']['coordinates'])
            self.save_to_history(start_address, end_address, route)

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Erreur", f"Problème de connexion : {str(e)}")
        except ValueError as e:
            messagebox.showerror("Erreur", str(e))
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur inattendue : {str(e)}")

    def display_route_info(self, route):
        """Afficher les informations de l'itinéraire"""
        try:
            distance = route['distance'] / 1000  # Conversion en km
            duration = route['duration'] / 60   # Conversion en minutes
            
            self.lbl_distance.config(text=f"Distance: {distance:.1f} km")
            self.lbl_duration.config(text=f"Durée: {duration:.0f} minutes")
        except KeyError:
            messagebox.showwarning("Information", "Données de trajet incomplètes")

    def create_map(self, start_coord, end_coord, route_points):
        """Générer la carte interactive"""
        try:
            m = folium.Map(location=start_coord, zoom_start=13)

            # Marqueurs
            folium.Marker(start_coord, 
                        popup='Départ',
                        icon=folium.Icon(color='green')).add_to(m)
            
            folium.Marker(end_coord, 
                        popup='Arrivée',
                        icon=folium.Icon(color='red')).add_to(m)

            # Tracé de l'itinéraire
            folium.PolyLine(
                [(point[1], point[0]) for point in route_points],
                color='blue',
                weight=3,
                opacity=0.7
            ).add_to(m)

            m.save('map.html')
            webbrowser.open('map.html')
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de génération de carte : {str(e)}")

    def save_to_history(self, start, end, route):
        """Sauvegarder dans l'historique"""
        entry = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'start': start,
            'end': end,
            'distance': route.get('distance', 0),
            'duration': route.get('duration', 0)
        }
        self.history.insert(0, entry)
        self.update_history_listbox()
        self.save_history()

    def update_history_listbox(self):
        """Mettre à jour l'affichage de l'historique"""
        self.history_listbox.delete(0, tk.END)
        for entry in self.history[:10]:
            text = f"{entry['timestamp']} | {entry['start'][:20]} -> {entry['end'][:20]}"
            self.history_listbox.insert(tk.END, text)

    def load_history_entry(self, event):
        """Charger une entrée de l'historique"""
        selection = self.history_listbox.curselection()
        if selection:
            try:
                entry = self.history[selection[0]]
                self.entry_start.delete(0, tk.END)
                self.entry_start.insert(0, entry['start'])
                self.entry_end.delete(0, tk.END)
                self.entry_end.insert(0, entry['end'])
            except IndexError:
                pass

    def save_history(self):
        """Sauvegarder l'historique dans un fichier"""
        try:
            with open('history.json', 'w') as f:
                json.dump(self.history, f)
        except Exception as e:
            print(f"Erreur sauvegarde historique: {str(e)}")

    def load_history(self):
        """Charger l'historique depuis un fichier"""
        try:
            with open('history.json', 'r') as f:
                self.history = json.load(f)
            self.update_history_listbox()
        except (FileNotFoundError, json.JSONDecodeError):
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = GeoApp(root)
    root.mainloop()