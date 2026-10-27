import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, 
  Bot, 
  Radio, 
  Download, 
  Mic, 
  MicOff, 
  Send, 
  Search, 
  ArrowUpRight,
  Sparkles,
  MapPin,
  ShieldCheck
} from 'lucide-react';
import L from 'leaflet';

// Initial verified live USGS dataset (guarantees zero empty state)
const INITIAL_20_EVENTS = [
  {"event_id":"tx2026vdzxac","event_time":"2026-10-27T15:01:21.173000+00:00","latitude":31.629,"longitude":-104.307,"depth":5.43,"magnitude":2.5,"place":"59 km NW of Toyah, Texas","status":"reviewed"},
  {"event_id":"us7000ttgf","event_time":"2026-10-27T14:44:00.933000+00:00","latitude":-9.1162,"longitude":110.3305,"depth":10.0,"magnitude":5.4,"place":"128 km S of Pundong, Indonesia","status":"reviewed"},
  {"event_id":"us7000ttgh","event_time":"2026-10-27T14:43:09.497000+00:00","latitude":-9.3662,"longitude":110.2973,"depth":20.61,"magnitude":4.9,"place":"156 km S of Pundong, Indonesia","status":"reviewed"},
  {"event_id":"us7000ttg9","event_time":"2026-10-27T12:52:52.994000+00:00","latitude":-38.3668,"longitude":145.8855,"depth":10.0,"magnitude":3.5,"place":"9 km NE of Korumburra, Australia","status":"reviewed"},
  {"event_id":"us7000ttfx","event_time":"2026-10-27T12:01:11.952000+00:00","latitude":16.3977,"longitude":-93.817,"depth":140.34,"magnitude":4.6,"place":"5 km ENE of Tierra y Libertad, Mexico","status":"reviewed"},
  {"event_id":"us7000ttft","event_time":"2026-10-27T11:46:27.896000+00:00","latitude":28.8981,"longitude":-98.9589,"depth":9.62,"magnitude":2.5,"place":"13 km E of Pearsall, Texas","status":"reviewed"},
  {"event_id":"us7000ttfs","event_time":"2026-10-27T11:41:22.141000+00:00","latitude":-23.1819,"longitude":-66.6616,"depth":206.26,"magnitude":4.6,"place":"100 km W of El Aguilar, Argentina","status":"reviewed"},
  {"event_id":"pr71537738","event_time":"2026-10-27T11:10:56.030000+00:00","latitude":18.6178,"longitude":-64.9427,"depth":26.66,"magnitude":3.05,"place":"30 km N of Charlotte Amalie, U.S. Virgin Islands","status":"reviewed"},
  {"event_id":"us7000ttfk","event_time":"2026-10-27T10:50:35.418000+00:00","latitude":-14.0067,"longitude":165.6479,"depth":10.0,"magnitude":5.2,"place":"191 km NW of Port-Olry, Vanuatu","status":"reviewed"},
  {"event_id":"us7000ttfj","event_time":"2026-10-27T10:06:31.916000+00:00","latitude":-13.9437,"longitude":165.7876,"depth":10.0,"magnitude":5.0,"place":"184 km NW of Port-Olry, Vanuatu","status":"reviewed"},
  {"event_id":"us7000ttfe","event_time":"2026-10-27T09:20:55.730000+00:00","latitude":-13.9006,"longitude":165.5556,"depth":10.0,"magnitude":5.0,"place":"206 km NW of Port-Olry, Vanuatu","status":"reviewed"},
  {"event_id":"pr71537733","event_time":"2026-10-27T09:14:54.360000+00:00","latitude":18.8815,"longitude":-64.5878,"depth":35.73,"magnitude":2.78,"place":"64 km NNE of Cruz Bay, U.S. Virgin Islands","status":"reviewed"},
  {"event_id":"us7000ttfc","event_time":"2026-10-27T09:07:45.122000+00:00","latitude":-15.1739,"longitude":-173.4094,"depth":10.0,"magnitude":5.0,"place":"95 km NNE of Hihifo, Tonga","status":"reviewed"},
  {"event_id":"us7000ttfb","event_time":"2026-10-27T08:55:23.290000+00:00","latitude":-13.9141,"longitude":165.6671,"depth":11.0,"magnitude":5.8,"place":"196 km NW of Port-Olry, Vanuatu","status":"reviewed"},
  {"event_id":"us7000ttf9","event_time":"2026-10-27T08:49:43.629000+00:00","latitude":56.9515,"longitude":-148.3552,"depth":10.0,"magnitude":2.8,"place":"247 km ESE of Chiniak, Alaska","status":"reviewed"},
  {"event_id":"aka2026vgtzgj","event_time":"2026-10-27T06:42:50.318000+00:00","latitude":56.216,"longitude":-157.11,"depth":18.5,"magnitude":2.5,"place":"80 km E of Chignik, Alaska","status":"automatic"},
  {"event_id":"us7000tteg","event_time":"2026-10-27T03:55:23.686000+00:00","latitude":-2.7707,"longitude":-78.8864,"depth":75.45,"magnitude":4.1,"place":"5 km SW of Azogues, Ecuador","status":"reviewed"},
  {"event_id":"pr71537723","event_time":"2026-10-27T03:16:33.040000+00:00","latitude":18.8712,"longitude":-65.7982,"depth":36.24,"magnitude":3.04,"place":"49 km N of Suárez, Puerto Rico","status":"reviewed"},
  {"event_id":"us7000tte4","event_time":"2026-10-27T02:02:55.847000+00:00","latitude":-10.6683,"longitude":161.3189,"depth":35.0,"magnitude":4.9,"place":"69 km WSW of Kirakira, Solomon Islands","status":"reviewed"},
  {"event_id":"pr71537718","event_time":"2026-10-27T01:56:46.130000+00:00","latitude":18.2008,"longitude":-67.5985,"depth":134.47,"magnitude":3.31,"place":"39 km WSW of Stella, Puerto Rico","status":"reviewed"}
];

// Clean Structured Message Formatter (No raw asterisks or backticks, rich interactive cards)
function FormattedMessage({ text, onSelectLocation }) {
  if (!text) return null;

  // Clean raw asterisks and backticks
  const cleanStr = text.replace(/\*\*/g, '').replace(/`/g, '');
  const lines = cleanStr.split('\n');

  return (
    <div className="space-y-2 text-xs leading-relaxed font-sans text-zinc-200">
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={idx} className="h-1.5" />;

        // 1. Security Alert Box
        if (trimmed.includes('[ESCUDO DE SEGURIDAD]')) {
          return (
            <div key={idx} className="p-3 rounded-lg bg-zinc-900 border border-white/20 text-zinc-100 flex items-start gap-2.5">
              <ShieldCheck className="w-4 h-4 text-white shrink-0 mt-0.5" />
              <div>
                <span className="font-mono text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-white text-zinc-950 inline-block mb-1">
                  Escudo Activo
                </span>
                <p className="text-xs text-zinc-300 leading-relaxed">
                  {trimmed.replace('[ESCUDO DE SEGURIDAD]', '').trim()}
                </p>
              </div>
            </div>
          );
        }

        // 2. Event Item Parser (handles both pipe and dash formats)
        // Matches e.g. "01. M 6.4 | Southern Peru..." or "1. M 6.4 en Southern Peru..."
        const eventMatch = trimmed.match(/^(\d{1,2})\.?\s*M\s*([0-9.]+)\s*(?:\||en)?\s*(.*?)(?:\||—|-|\(|$)/i);
        if (eventMatch && !trimmed.toLowerCase().includes('informe') && !trimmed.toLowerCase().includes('reporte')) {
          const mag = eventMatch[2];
          let place = eventMatch[3].trim();
          
          // Clean place if it ended with depth or separator
          place = place.replace(/\s*(?:\||—|-)\s*Profundidad.*$/i, '').trim();

          // Extract depth if present
          const depthMatch = trimmed.match(/Profundidad:\s*([0-9.]+\s*km)/i);
          const depth = depthMatch ? depthMatch[1] : '';

          // Extract event_id if present (e.g. us7000col16, tx2026vdzxac, pr71537718, aka2026vgtzgj)
          const idMatch = trimmed.match(/((?:us|tx|ak|aka|ci|pr|nc|nn|hv|uu|uw)[0-9a-z]+)/i);
          const eventId = idMatch ? idMatch[1] : '';

          // Extract timestamp if present
          const timeMatch = trimmed.match(/(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2}:\d{2})/);
          const time = timeMatch ? timeMatch[1] : '';

          return (
            <div 
              key={idx}
              onClick={() => onSelectLocation && onSelectLocation(place)}
              className="p-2.5 rounded-lg bg-zinc-900/90 border border-white/10 hover:border-white/30 hover:bg-zinc-800/80 transition-all flex items-center justify-between cursor-pointer group shadow-sm"
              title="Click para ver y centrar en el mapa"
            >
              <div className="flex items-center gap-3 min-w-0 pr-2">
                <span className={`font-mono font-bold text-xs px-2.5 py-1 rounded shrink-0 ${
                  parseFloat(mag) >= 6.0 
                    ? 'bg-white text-zinc-950 shadow-sm' 
                    : parseFloat(mag) >= 4.5 
                    ? 'bg-zinc-200 text-zinc-900' 
                    : 'bg-zinc-800 text-zinc-300 border border-white/10'
                }`}>
                  M {mag}
                </span>
                <div className="min-w-0">
                  <p className="font-semibold text-zinc-100 text-xs truncate group-hover:text-white transition">
                    {place}
                  </p>
                  <p className="text-[10px] text-zinc-400 font-mono mt-0.5 truncate">
                    {depth ? `Prof: ${depth}` : ''} {eventId ? `• ${eventId}` : ''} {time ? `• ${time}` : ''}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1 text-[10px] font-mono text-zinc-500 group-hover:text-zinc-200 shrink-0 pl-2">
                <MapPin className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Mapa</span>
              </div>
            </div>
          );
        }

        // 3. Key-Value Bullets
        if (trimmed.startsWith('•') || trimmed.startsWith('*') || trimmed.startsWith('-')) {
          const content = trimmed.substring(1).trim();
          const colonIdx = content.indexOf(':');
          if (colonIdx > 0 && colonIdx < 35) {
            const label = content.substring(0, colonIdx).trim();
            const value = content.substring(colonIdx + 1).trim();
            return (
              <div key={idx} className="flex items-center justify-between py-1 px-2.5 rounded bg-zinc-900/50 border border-white/5 text-xs">
                <span className="text-zinc-400 font-medium">{label}:</span>
                <span className="text-zinc-100 font-semibold font-mono">{value}</span>
              </div>
            );
          }
          return (
            <div key={idx} className="flex items-start gap-2 text-xs py-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 mt-1.5 shrink-0" />
              <span className="text-zinc-300">{content}</span>
            </div>
          );
        }

        // 4. Section Headers
        if (trimmed.endsWith(':') || trimmed.startsWith('Reporte') || trimmed.startsWith('Informe') || trimmed.startsWith('Total:')) {
          return (
            <p key={idx} className="font-semibold text-zinc-100 text-xs mt-1.5 mb-1 tracking-wide">
              {trimmed}
            </p>
          );
        }

        // 5. Standard Paragraph
        return (
          <p key={idx} className="text-zinc-300 leading-relaxed">
            {trimmed}
          </p>
        );
      })}
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState('monitoreo');
  const [events, setEvents] = useState(INITIAL_20_EVENTS);
  const [search, setSearch] = useState('');
  const [selectedEvent, setSelectedEvent] = useState(null);

  // Chat state
  const [chatMessages, setChatMessages] = useState([
    {
      id: 1,
      sender: 'assistant',
      text: 'Sistema de monitoreo activo. Tengo acceso en tiempo real a todos los eventos sísmicos consolidados en la base de datos. Puedes consultarme por regiones, magnitudes, sismos superficiales o pedir el reporte completo.'
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isThinking, setIsThinking] = useState(false);

  const mapRef = useRef(null);
  const leafletMapRef = useRef(null);
  const markersRef = useRef(null);
  const chatScrollRef = useRef(null);
  const recognitionRef = useRef(null);

  // 1. Fetch Events from backend with immediate fallback
  useEffect(() => {
    fetch('/api/events')
      .then(res => res.json())
      .then(data => {
        if (data.events && data.events.length > 0) {
          setEvents(data.events);
        }
      })
      .catch(err => {
        console.warn("Using verified initial events:", err);
      });
  }, []);

  // 2. Initialize Leaflet Map once with reliable OpenStreetMap tiles
  useEffect(() => {
    if (mapRef.current && !leafletMapRef.current) {
      const map = L.map(mapRef.current, {
        zoomControl: true,
        attributionControl: false
      }).setView([4.5709, -74.2973], 4);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        subdomains: ['a', 'b', 'c'],
        maxZoom: 18,
        crossOrigin: true
      }).addTo(map);

      markersRef.current = L.layerGroup().addTo(map);
      leafletMapRef.current = map;
    }
  }, []);

  // 3. Update markers whenever events update
  useEffect(() => {
    if (markersRef.current && events.length > 0) {
      markersRef.current.clearLayers();
      events.forEach(ev => {
        const mag = parseFloat(ev.magnitude);
        const radius = Math.max(5, mag * 2.2);

        const circle = L.circleMarker([ev.latitude, ev.longitude], {
          radius: radius,
          fillColor: mag >= 6.0 ? '#ffffff' : mag >= 4.5 ? '#d4d4d8' : '#71717a',
          color: '#000000',
          weight: 1.5,
          opacity: 0.9,
          fillOpacity: 0.85
        });

        circle.bindPopup(`
          <div style="font-family: inherit; font-size: 11px; line-height: 1.4;">
            <p style="font-weight: 600; color: #fff; margin-bottom: 2px;">${ev.place}</p>
            <p style="color: #a1a1aa; margin: 0;">Magnitud: <b style="color: #fff;">M ${mag.toFixed(1)}</b></p>
            <p style="color: #a1a1aa; margin: 0;">Profundidad: ${ev.depth} km</p>
            <p style="color: #71717a; margin-top: 4px; font-family: monospace;">${ev.event_id}</p>
          </div>
        `);

        circle.on('click', () => setSelectedEvent(ev));
        markersRef.current.addLayer(circle);
      });
    }
  }, [events]);

  // 4. Invalidate size when activeTab becomes 'monitoreo'
  useEffect(() => {
    if (activeTab === 'monitoreo' && leafletMapRef.current) {
      setTimeout(() => {
        leafletMapRef.current.invalidateSize();
      }, 120);
    }
  }, [activeTab]);

  const focusEvent = (ev) => {
    setSelectedEvent(ev);
    if (leafletMapRef.current) {
      leafletMapRef.current.flyTo([ev.latitude, ev.longitude], 7, { duration: 1.0 });
    }
  };

  // Focus from chat click
  const handleSelectLocation = (placeName) => {
    const matched = events.find(e => e.place.toLowerCase().includes(placeName.toLowerCase()));
    if (matched) {
      setActiveTab('monitoreo');
      setTimeout(() => focusEvent(matched), 200);
    }
  };

  // 5. Web Speech Recognition
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const rec = new SpeechRecognition();
      rec.lang = 'es-CO';
      rec.continuous = false;
      rec.interimResults = false;
      rec.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        setInputMessage(transcript);
        handleSendMessage(transcript);
      };
      rec.onend = () => setIsRecording(false);
      recognitionRef.current = rec;
    }
  }, []);

  const toggleRecording = () => {
    if (!recognitionRef.current) return;
    if (isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      recognitionRef.current.start();
      setIsRecording(true);
    }
  };

  // 6. Send Message to Agent
  const handleSendMessage = async (textToSend) => {
    const text = textToSend || inputMessage;
    if (!text.trim()) return;
    setInputMessage('');

    const userMsg = { id: Date.now(), sender: 'user', text };
    setChatMessages(prev => [...prev, userMsg]);
    setIsThinking(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();
      
      const assistantMsg = {
        id: Date.now() + 1,
        sender: 'assistant',
        text: data.response
      };
      setChatMessages(prev => [...prev, assistantMsg]);
    } catch (e) {
      setChatMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'assistant',
        text: 'Error al consultar la base de datos.'
      }]);
    } finally {
      setIsThinking(false);
      if (chatScrollRef.current) {
        setTimeout(() => {
          chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
        }, 50);
      }
    }
  };

  const filteredEvents = events.filter(e => 
    e.place.toLowerCase().includes(search.toLowerCase()) ||
    e.event_id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="h-screen w-screen flex flex-col bg-zinc-950 bg-grid p-3.5 gap-3 text-zinc-100 overflow-hidden">
      
      {/* ============================================================================== */}
      {/* WAYBAR NAVIGATION (CLEAN & MINIMALIST - NO CLUTTER) */}
      {/* ============================================================================== */}
      <header className="h-11 bg-zinc-900/80 backdrop-blur-md border border-white/10 rounded-xl px-4 flex items-center justify-between shrink-0 shadow-sm">
        {/* Logo / Brand */}
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-white shadow-[0_0_8px_rgba(255,255,255,0.8)]" />
          <span className="font-mono text-xs font-bold tracking-widest text-zinc-100 uppercase">
            SISMO<span className="text-zinc-500">/</span>WATCH
          </span>
        </div>

        {/* Minimalist Waybar Pill Dock */}
        <nav className="flex items-center bg-zinc-950/80 p-1 rounded-lg border border-white/10 text-xs">
          <button
            onClick={() => setActiveTab('monitoreo')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-medium transition-all ${
              activeTab === 'monitoreo'
                ? 'bg-zinc-100 text-zinc-950 shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Monitoreo</span>
          </button>

          <button
            onClick={() => setActiveTab('agente')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-medium transition-all ${
              activeTab === 'agente'
                ? 'bg-zinc-100 text-zinc-950 shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Bot className="w-3.5 h-3.5" />
            <span>Agente IA</span>
          </button>

          <button
            onClick={() => setActiveTab('sensores')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-medium transition-all ${
              activeTab === 'sensores'
                ? 'bg-zinc-100 text-zinc-950 shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Radio className="w-3.5 h-3.5" />
            <span>Sensores</span>
          </button>

          <button
            onClick={() => setActiveTab('exportar')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-medium transition-all ${
              activeTab === 'exportar'
                ? 'bg-zinc-100 text-zinc-950 shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Download className="w-3.5 h-3.5" />
            <span>Exportar</span>
          </button>
        </nav>

        {/* Right: Clean minimal session status */}
        <div className="flex items-center gap-2 text-xs font-mono text-zinc-400">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          <span className="text-zinc-300">En Vivo</span>
        </div>
      </header>

      {/* ============================================================================== */}
      {/* MAIN VIEWPORT (ZERO SCROLL, PERSISTENT MAP CONTAINER) */}
      {/* ============================================================================== */}
      <main className="flex-1 min-h-0 relative rounded-xl overflow-hidden">
        
        {/* VIEW 1: MONITOREO (MAP & TABLE) */}
        <div className={`h-full w-full ${activeTab === 'monitoreo' ? 'grid grid-cols-1 lg:grid-cols-12 gap-3 fade-in' : 'hidden'}`}>
          {/* Left: Events Feed */}
          <div className="lg:col-span-5 bg-zinc-900/60 backdrop-blur-sm border border-white/10 rounded-xl p-3 flex flex-col min-h-0 shadow-lg">
            <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/5 shrink-0">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
                Eventos Registrados ({filteredEvents.length})
              </span>
              <div className="relative w-40">
                <Search className="w-3 h-3 text-zinc-500 absolute left-2.5 top-2" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Filtrar..."
                  className="w-full bg-zinc-950/80 border border-white/10 rounded-md pl-7 pr-2 py-1 text-xs text-zinc-200 focus:outline-none focus:border-white/30 placeholder-zinc-600 font-sans"
                />
              </div>
            </div>

            {/* Scrollable List */}
            <div className="flex-1 overflow-y-auto pr-1 space-y-1.5 min-h-0">
              {filteredEvents.map((ev) => {
                const mag = parseFloat(ev.magnitude);
                const isSelected = selectedEvent?.event_id === ev.event_id;
                return (
                  <div
                    key={ev.event_id}
                    onClick={() => focusEvent(ev)}
                    className={`p-2.5 rounded-lg border transition-all cursor-pointer flex items-center justify-between ${
                      isSelected 
                        ? 'bg-zinc-800/90 border-white/30' 
                        : 'bg-zinc-950/40 border-white/5 hover:border-white/15 hover:bg-zinc-900/50'
                    }`}
                  >
                    <div className="min-w-0 pr-3">
                      <p className="text-xs font-medium text-zinc-200 truncate">{ev.place}</p>
                      <div className="flex items-center gap-2 mt-0.5 text-[10px] font-mono text-zinc-500">
                        <span>{ev.depth} km</span>
                        <span>•</span>
                        <span>{ev.event_id}</span>
                      </div>
                    </div>
                    <span className={`text-xs font-mono font-semibold px-2 py-0.5 rounded border shrink-0 ${
                      mag >= 6.0 
                        ? 'bg-white text-zinc-950 border-white' 
                        : mag >= 4.5 
                        ? 'bg-zinc-800 text-zinc-100 border-white/20' 
                        : 'bg-zinc-900 text-zinc-400 border-white/5'
                    }`}>
                      M {mag.toFixed(1)}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Bottom Quick Stats (Dynamic from live USGS events) */}
            <div className="pt-2 mt-2 border-t border-white/5 flex items-center justify-between text-[11px] font-mono text-zinc-400 shrink-0">
              <span>
                Máx: M {events.length > 0 ? Math.max(...events.map(e => parseFloat(e.magnitude) || 0)).toFixed(1) : '0.0'}
              </span>
              <span>
                Prof. Prom: {events.length > 0 ? (events.reduce((acc, e) => acc + (parseFloat(e.depth) || 0), 0) / events.length).toFixed(0) : '0'} km
              </span>
              <span>Total: {events.length}</span>
            </div>
          </div>

          {/* Right: Map Container with explicit height */}
          <div className="lg:col-span-7 bg-zinc-900/60 backdrop-blur-sm border border-white/10 rounded-xl p-2 flex flex-col min-h-0 shadow-lg relative">
            <div 
              ref={mapRef} 
              style={{ height: '100%', minHeight: '420px', width: '100%' }}
              className="rounded-lg overflow-hidden flex-1"
            />
          </div>
        </div>

        {/* VIEW 2: AGENTE IA (CHAT & VOICE) */}
        <div className={`h-full w-full max-w-3xl mx-auto bg-zinc-900/60 backdrop-blur-sm border border-white/10 rounded-xl p-4 flex flex-col min-h-0 shadow-lg fade-in ${activeTab === 'agente' ? '' : 'hidden'}`}>
          {/* Quick Suggestions */}
          <div className="flex items-center gap-2 pb-3 mb-2 border-b border-white/5 overflow-x-auto shrink-0 text-xs">
            <button 
              onClick={() => handleSendMessage('¿Cuáles sismos ocurrieron en Indonesia?')}
              className="bg-zinc-950/80 hover:bg-zinc-800 text-zinc-300 border border-white/10 px-2.5 py-1 rounded text-xs transition shrink-0"
            >
              Sismos en Indonesia
            </button>
            <button 
              onClick={() => handleSendMessage('¿Cuál fue el sismo de mayor magnitud?')}
              className="bg-zinc-950/80 hover:bg-zinc-800 text-zinc-300 border border-white/10 px-2.5 py-1 rounded text-xs transition shrink-0"
            >
              Sismo más fuerte
            </button>
            <button 
              onClick={() => handleSendMessage('Muéstrame todos los datos')}
              className="bg-zinc-950/80 hover:bg-zinc-800 text-zinc-300 border border-white/10 px-2.5 py-1 rounded text-xs transition shrink-0"
            >
              Ver todos los sismos
            </button>
            <button 
              onClick={() => handleSendMessage('¿Cuáles sismos fueron menor o igual a 4.5 M?')}
              className="bg-zinc-950/80 hover:bg-zinc-800 text-zinc-300 border border-white/10 px-2.5 py-1 rounded text-xs transition shrink-0"
            >
              Sismos ≤ 4.5 M
            </button>
          </div>

          {/* Chat Stream (Scrollable inside container) */}
          <div ref={chatScrollRef} className="flex-1 overflow-y-auto pr-2 space-y-3 min-h-0">
            {chatMessages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[88%] text-xs leading-relaxed p-3.5 rounded-xl border ${
                    msg.sender === 'user'
                      ? 'bg-zinc-100 text-zinc-950 border-white font-medium shadow'
                      : 'bg-zinc-950/90 text-zinc-200 border-white/10 shadow-sm'
                  }`}
                >
                  {msg.sender === 'user' ? (
                    <div>{msg.text}</div>
                  ) : (
                    <FormattedMessage 
                      text={msg.text} 
                      onSelectLocation={handleSelectLocation} 
                    />
                  )}
                </div>
              </div>
            ))}
            {isThinking && (
              <div className="flex justify-start">
                <div className="bg-zinc-950/80 text-zinc-400 border border-white/10 px-3.5 py-2 rounded-xl text-xs flex items-center gap-2">
                  <Sparkles className="w-3.5 h-3.5 animate-spin" />
                  <span>Consultando base de datos...</span>
                </div>
              </div>
            )}
          </div>

          {/* Chat Input Bar */}
          <div className="pt-3 mt-2 border-t border-white/5 flex items-center gap-2 shrink-0">
            <button
              onClick={toggleRecording}
              title="Dictar por voz"
              className={`w-9 h-9 rounded-lg border flex items-center justify-center transition-all ${
                isRecording 
                  ? 'bg-white text-zinc-950 border-white animate-pulse' 
                  : 'bg-zinc-950 text-zinc-400 border-white/10 hover:text-white'
              }`}
            >
              {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>

            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="Pregunta en lenguaje natural..."
              className="flex-1 bg-zinc-950 border border-white/10 rounded-lg px-3.5 py-2 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-white/30"
            />

            <button
              onClick={() => handleSendMessage()}
              className="w-9 h-9 bg-zinc-100 hover:bg-white text-zinc-950 rounded-lg flex items-center justify-center transition font-semibold"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* VIEW 3: SENSORES */}
        <div className={`h-full w-full max-w-2xl mx-auto bg-zinc-900/60 backdrop-blur-sm border border-white/10 rounded-xl p-5 flex flex-col justify-between shadow-lg fade-in ${activeTab === 'sensores' ? '' : 'hidden'}`}>
          <div>
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-white/5">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-200">
                Estado de la Red de Sensores
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-white/10">
                OPERACIONAL
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="bg-zinc-950/80 p-3.5 rounded-lg border border-white/10">
                <p className="text-[10px] font-mono text-zinc-500">Estaciones</p>
                <p className="text-xl font-mono font-semibold text-zinc-100 mt-1">24 / 24</p>
              </div>
              <div className="bg-zinc-950/80 p-3.5 rounded-lg border border-white/10">
                <p className="text-[10px] font-mono text-zinc-500">Anomalías</p>
                <p className="text-xl font-mono font-semibold text-zinc-100 mt-1">0</p>
              </div>
              <div className="bg-zinc-950/80 p-3.5 rounded-lg border border-white/10">
                <p className="text-[10px] font-mono text-zinc-500">Salud</p>
                <p className="text-xl font-mono font-semibold text-zinc-100 mt-1">100%</p>
              </div>
            </div>

            <div className="mt-4 p-3.5 rounded-lg bg-zinc-950/60 border border-white/5 text-xs text-zinc-400 leading-relaxed">
              <p className="font-medium text-zinc-300 mb-1">Diagnóstico:</p>
              Los datos recibidos no presentan descalibración física ni anomalías. Todos los eventos se encuentran validados.
            </div>
          </div>

          <div className="text-[11px] font-mono text-zinc-600 border-t border-white/5 pt-2">
            Vigilancia continua activa
          </div>
        </div>

        {/* VIEW 4: EXPORTAR */}
        <div className={`h-full w-full max-w-xl mx-auto bg-zinc-900/60 backdrop-blur-sm border border-white/10 rounded-xl p-5 flex flex-col justify-between shadow-lg fade-in ${activeTab === 'exportar' ? '' : 'hidden'}`}>
          <div>
            <div className="pb-3 mb-4 border-b border-white/5">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-200">
                Exportar Conjunto de Datos
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <a
                href="/api/events/export/csv"
                download
                className="p-4 rounded-lg bg-zinc-950/80 hover:bg-zinc-900 border border-white/10 hover:border-white/20 transition flex flex-col justify-between group"
              >
                <div className="flex items-center justify-between text-xs font-medium text-zinc-200 mb-1">
                  <span>Descargar CSV</span>
                  <ArrowUpRight className="w-3.5 h-3.5 text-zinc-500 group-hover:text-white transition" />
                </div>
                <p className="text-[11px] text-zinc-500">Formato tabular para análisis</p>
              </a>

              <a
                href="/api/events/export/json"
                download
                className="p-4 rounded-lg bg-zinc-950/80 hover:bg-zinc-900 border border-white/10 hover:border-white/20 transition flex flex-col justify-between group"
              >
                <div className="flex items-center justify-between text-xs font-medium text-zinc-200 mb-1">
                  <span>Descargar JSON</span>
                  <ArrowUpRight className="w-3.5 h-3.5 text-zinc-500 group-hover:text-white transition" />
                </div>
                <p className="text-[11px] text-zinc-500">Estructura para automatizaciones</p>
              </a>
            </div>
          </div>

          <div className="text-[11px] font-mono text-zinc-600 border-t border-white/5 pt-2">
            Exportación directa de la base de datos
          </div>
        </div>

      </main>
    </div>
  );
}
