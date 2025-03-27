import { useState, useEffect } from 'react'
import MapComponent from '../components/MapComponent'
import Chatbot from '../components/Chatbot'

export default function Home() {
  const [tripData, setTripData] = useState(null)
  const [ws, setWs] = useState<WebSocket | null>(null)

  useEffect(() => {
    // Connect to WebSocket
    const socket = new WebSocket('ws://localhost:8000/ws/trip/123')
    setWs(socket)
    
    return () => socket.close()
  }, [])

  const planTrip = async () => {
    const response = await fetch('http://localhost:8000/api/plan-trip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        origin: 'Pune',
        destination: 'Manali',
        start_date: '2024-12-01',
        end_date: '2024-12-07',
        budget: 50000,
        interests: ['adventure', 'nature']
      })
    })
    setTripData(await response.json())
  }

  return (
    <div className="container">
      <button onClick={planTrip}>Plan My Trip</button>
      
      {tripData && (
        <>
          <MapComponent directions={tripData.directions} />
          <div className="recommendations">
            {tripData.recommendations.map((item, i) => (
              <div key={i}>{item.name}</div>
            ))}
          </div>
        </>
      )}
      
      <Chatbot />
    </div>
  )
}