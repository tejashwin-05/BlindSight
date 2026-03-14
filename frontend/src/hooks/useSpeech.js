import { useRef, useCallback, useEffect } from 'react'

function useSpeech() {
  const utteranceRef = useRef(null)
  const voiceRef = useRef(null)

  // Load voices when available
  useEffect(() => {
    const loadVoices = () => {
      const voices = window.speechSynthesis.getVoices()
      // Prefer English voices
      const englishVoice = voices.find(v => v.lang.startsWith('en-'))
      if (englishVoice) {
        voiceRef.current = englishVoice
        console.log('[Speech] Using voice:', englishVoice.name)
      }
    }

    loadVoices()
    window.speechSynthesis.onvoiceschanged = loadVoices
  }, [])

  const speak = useCallback((text) => {
    // Cancel any ongoing speech
    window.speechSynthesis.cancel()

    if (!text) return

    console.log('[Speech] Speaking:', text)

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = 1.1  // Slightly faster for urgency
    utterance.pitch = 1.0
    utterance.volume = 1.0
    utterance.lang = 'en-US'
    
    if (voiceRef.current) {
      utterance.voice = voiceRef.current
    }

    utterance.onerror = (event) => {
      console.error('[Speech] Error:', event.error)
    }

    utterance.onend = () => {
      console.log('[Speech] Finished speaking')
    }

    utteranceRef.current = utterance
    window.speechSynthesis.speak(utterance)
  }, [])

  const stopSpeaking = useCallback(() => {
    console.log('[Speech] Stopping speech')
    window.speechSynthesis.cancel()
  }, [])

  return {
    speak,
    stopSpeaking
  }
}

export default useSpeech
