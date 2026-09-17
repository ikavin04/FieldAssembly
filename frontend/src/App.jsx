import VoiceTestPanel from './components/VoiceTestPanel'

function App() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-950 text-white">
      <h1 className="text-5xl font-bold tracking-tight mb-4">FieldVoice</h1>
      <p className="text-lg text-gray-400 mb-8">
        Hands-Free AI Copilot for Field Workers
      </p>
      <VoiceTestPanel />
    </div>
  )
}

export default App
