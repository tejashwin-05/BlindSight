import { useState, useEffect, useRef, useCallback } from 'react';

// Haversine distance in metres between two {lat,lng} points
function haversine(a, b) {
  const R = 6371000;
  const dLat = (b.lat - a.lat) * Math.PI / 180;
  const dLng = (b.lng - a.lng) * Math.PI / 180;
  const sin2 = Math.sin(dLat / 2) ** 2
    + Math.cos(a.lat * Math.PI / 180) * Math.cos(b.lat * Math.PI / 180)
    * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.asin(Math.sqrt(sin2));
}

// How close (metres) user must be to a waypoint to trigger the next instruction
const TRIGGER_RADIUS = 25;
// How far ahead (metres) to pre-announce the upcoming instruction
const PREANNOUNCE_RADIUS = 40;

export default function useNavigation(steps, userLocation) {
  const [activeStep,    setActiveStep]    = useState(0);
  const [arrived,       setArrived]       = useState(false);
  const [distToNext,    setDistToNext]    = useState(null);
  const spokenRef   = useRef(new Set());   // track which steps have been spoken
  const activeRef   = useRef(0);

  // Speak via browser TTS
  const speak = useCallback((text) => {
    if (!text) return;
    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(text);
    utt.rate = 0.95; utt.pitch = 1;
    window.speechSynthesis.speak(utt);
  }, []);

  // Reset when a new route is loaded
  useEffect(() => {
    if (!steps || steps.length === 0) return;
    setActiveStep(0);
    setArrived(false);
    setDistToNext(null);
    spokenRef.current = new Set();
    activeRef.current = 0;
    // Speak the first instruction immediately
    speak(steps[0].instruction);
    spokenRef.current.add(0);
  }, [steps]); // eslint-disable-line

  // Watch user location and advance checkpoints
  useEffect(() => {
    if (!steps || steps.length === 0 || !userLocation || arrived) return;

    const current = activeRef.current;
    const step    = steps[current];
    if (!step) return;

    // Distance to the NEXT step's waypoint (= end of current step)
    const nextStep = steps[current + 1];
    const target   = nextStep?.waypoint || steps[steps.length - 1]?.waypoint;
    if (!target) return;

    const dist = haversine(userLocation, target);
    setDistToNext(Math.round(dist));

    // Pre-announce: when approaching the waypoint, speak the NEXT instruction
    if (dist <= PREANNOUNCE_RADIUS && nextStep && !spokenRef.current.has(current + 1)) {
      spokenRef.current.add(current + 1);
      speak(nextStep.instruction);
    }

    // Checkpoint reached: advance active step
    if (dist <= TRIGGER_RADIUS) {
      const next = current + 1;
      if (next >= steps.length - 1) {
        // Last step = arrived
        setArrived(true);
        setActiveStep(steps.length - 1);
        activeRef.current = steps.length - 1;
        speak('You have arrived at your destination.');
      } else {
        setActiveStep(next);
        activeRef.current = next;
      }
    }
  }, [userLocation, steps, arrived, speak]);

  return { activeStep, arrived, distToNext };
}
