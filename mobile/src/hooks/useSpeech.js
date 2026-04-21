import { useCallback, useRef } from 'react';
import * as Speech from 'expo-speech';

/**
 * TTS hook using expo-speech.
 * Queues utterances and prevents overlap.
 */
export default function useSpeech() {
  const speakingRef = useRef(false);

  const speak = useCallback((text) => {
    if (!text) return;
    // Stop current speech before starting new one
    Speech.stop();
    Speech.speak(text, {
      language: 'en-US',
      rate: 0.95,
      pitch: 1.0,
      onStart: () => { speakingRef.current = true; },
      onDone: () => { speakingRef.current = false; },
      onError: () => { speakingRef.current = false; },
    });
  }, []);

  const stopSpeaking = useCallback(() => {
    Speech.stop();
    speakingRef.current = false;
  }, []);

  return { speak, stopSpeaking };
}
