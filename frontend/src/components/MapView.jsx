import React, { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import './MapView.css'

// Fix for default marker icons in Leaflet
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

// Custom photo marker icon
const createPhotoIcon = (count) => {
  return L.divIcon({
    className: 'custom-photo-marker',
    html: `<div class="photo-marker">
      <span class="photo-count">${count}</span>
    </div>`,
    iconSize: [40, 40],
    iconAnchor: [20, 40],
    popupAnchor: [0, -40]
  })
}

function MapView({ userId = 1, onImageClick }) {
  const [photos, setPhotos] = useState([])
  const [loading, setLoading] = useState(false)
  const [mapCenter, setMapCenter] = useState([20, 0]) // Default world center
  const [mapZoom, setMapZoom] = useState(2)

  useEffect(() => {
    fetchPhotosWithLocations()
  }, [userId])

  const fetchPhotosWithLocations = async () => {
    setLoading(true)
    try {
      // Fetch all photos
      const response = await fetch('/api/photos?limit=1000')
      if (response.ok) {
        const data = await response.json()
        const allPhotos = data.images || []

        // Fetch locations for each photo
        const photosWithLocations = []
        for (const photo of allPhotos) {
          try {
            const locResponse = await fetch(`/api/photos/${photo.id}/location`)
            if (locResponse.ok) {
              const locData = await locResponse.json()
              if (locData.location && locData.location.latitude && locData.location.longitude) {
                photosWithLocations.push({
                  ...photo,
                  location: locData.location
                })
              }
            }
          } catch (error) {
            console.error(`Error fetching location for photo ${photo.id}:`, error)
          }
        }

        setPhotos(photosWithLocations)

        // Center map on first photo if available
        if (photosWithLocations.length > 0) {
          const firstPhoto = photosWithLocations[0]
          setMapCenter([firstPhoto.location.latitude, firstPhoto.location.longitude])
          setMapZoom(4)
        }
      }
    } catch (error) {
      console.error('Error fetching photos with locations:', error)
    } finally {
      setLoading(false)
    }
  }

  // Group photos by location (within ~100m radius)
  const groupPhotosByLocation = () => {
    const groups = []
    const processed = new Set()

    photos.forEach((photo, index) => {
      if (processed.has(index)) return

      const group = {
        lat: photo.location.latitude,
        lng: photo.location.longitude,
        photos: [photo],
        location_name: photo.location.location_name || photo.location.city || 'Unknown Location'
      }

      // Find nearby photos (within ~100m)
      photos.forEach((otherPhoto, otherIndex) => {
        if (index === otherIndex || processed.has(otherIndex)) return

        const distance = getDistance(
          photo.location.latitude,
          photo.location.longitude,
          otherPhoto.location.latitude,
          otherPhoto.location.longitude
        )

        if (distance < 0.1) { // Less than 100m
          group.photos.push(otherPhoto)
          processed.add(otherIndex)
        }
      })

      processed.add(index)
      groups.push(group)
    })

    return groups
  }

  // Calculate distance between two coordinates (in km)
  const getDistance = (lat1, lon1, lat2, lon2) => {
    const R = 6371 // Earth's radius in km
    const dLat = (lat2 - lat1) * Math.PI / 180
    const dLon = (lon2 - lon1) * Math.PI / 180
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2)
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
    return R * c
  }

  const photoGroups = groupPhotosByLocation()

  if (loading) {
    return (
      <div className="map-view-loading">
        <div className="spinner"></div>
        <p>Loading map and photos...</p>
      </div>
    )
  }

  if (photos.length === 0) {
    return (
      <div className="map-view-empty">
        <h3>📍 No photos with location data</h3>
        <p>Upload photos with GPS information (EXIF data) to see them on the map.</p>
        <p className="hint">Most smartphones automatically add GPS coordinates to photos.</p>
      </div>
    )
  }

  return (
    <div className="map-view-container">
      <div className="map-view-header">
        <h2>🗺️ Photo Map</h2>
        <p>{photos.length} photo{photos.length !== 1 ? 's' : ''} with location data</p>
      </div>

      <div className="map-wrapper">
        <MapContainer
          center={mapCenter}
          zoom={mapZoom}
          className="photo-map"
          scrollWheelZoom={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {photoGroups.map((group, index) => (
            <Marker
              key={index}
              position={[group.lat, group.lng]}
              icon={createPhotoIcon(group.photos.length)}
            >
              <Popup maxWidth={400} className="photo-popup">
                <div className="popup-content">
                  <h4>{group.location_name}</h4>
                  <p className="photo-count-text">
                    {group.photos.length} photo{group.photos.length !== 1 ? 's' : ''}
                  </p>

                  <div className="popup-photos-grid">
                    {group.photos.slice(0, 6).map(photo => (
                      <div
                        key={photo.id}
                        className="popup-photo"
                        onClick={() => onImageClick && onImageClick(photo)}
                      >
                        <img
                          src={`http://localhost:8000${photo.file_path?.replace('./', '/')}`}
                          alt={photo.filename}
                        />
                      </div>
                    ))}
                  </div>

                  {group.photos.length > 6 && (
                    <p className="more-photos">
                      +{group.photos.length - 6} more photo{group.photos.length - 6 !== 1 ? 's' : ''}
                    </p>
                  )}
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>

      <div className="map-legend">
        <div className="legend-item">
          <div className="legend-icon"></div>
          <span>Click markers to view photos from that location</span>
        </div>
      </div>
    </div>
  )
}

export default MapView
