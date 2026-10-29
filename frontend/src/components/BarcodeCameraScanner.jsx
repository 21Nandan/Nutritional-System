import React, { useEffect, useRef, useState, useCallback } from 'react';
import { BrowserMultiFormatReader } from '@zxing/browser';
import { BarcodeFormat, DecodeHintType } from '@zxing/library';
import { 
  X, Zap, ZapOff, RefreshCw, AlertTriangle, 
  CheckCircle2, FlipHorizontal, Shield, Play, Pause, Keyboard
} from 'lucide-react';

/**
 * BarcodeCameraScanner component
 * - Uses ZXing BrowserMultiFormatReader configured specifically for retail food barcodes (EAN-13, EAN-8, UPC-A, UPC-E).
 * - Defaults to rear camera (facingMode: { ideal: "environment" }).
 * - Torch / flashlight toggle if supported by hardware & browser.
 * - Explicit controls: Start Scanning, Stop Scanning, Retry, Enter Barcode Manually.
 * - Throttles callbacks and validates length to prevent partial/duplicate triggers.
 * - Cleanly stops all camera tracks and loops on unmount / cancel.
 * - 100% client-side offline detection.
 */
export default function BarcodeCameraScanner({ onScan, onClose, onManualEntry, isScanningActive = true }) {
  const videoRef = useRef(null);
  const readerRef = useRef(null);
  const controlsRef = useRef(null);
  const scanLockRef = useRef(false);
  const lastScannedTimeRef = useRef(0);

  const [isLoading, setIsLoading] = useState(true);
  const [isScanning, setIsScanning] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [errorType, setErrorType] = useState(''); // 'permission', 'not_found', 'general', 'https'
  const [torchAvailable, setTorchAvailable] = useState(false);
  const [torchEnabled, setTorchEnabled] = useState(false);
  const [videoDevices, setVideoDevices] = useState([]);
  const [currentDeviceId, setCurrentDeviceId] = useState('');
  const [lastScannedCode, setLastScannedCode] = useState(null);

  // Play audio feedback beep using Web Audio API (offline, zero-file)
  const triggerAudioBeep = () => {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(920, ctx.currentTime);
      gain.gain.setValueAtTime(0.12, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.14);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.14);
    } catch {
      // The confirmation beep is optional; browsers may block audio until the user interacts.
    }
  };

  // Safely stop all active streams and tracks
  const stopStream = useCallback(() => {
    try {
      if (controlsRef.current) {
        controlsRef.current.stop();
        controlsRef.current = null;
      }
    } catch (e) {
      console.warn('Error stopping ZXing controls:', e);
    }

    try {
      if (videoRef.current && videoRef.current.srcObject) {
        const stream = videoRef.current.srcObject;
        stream.getTracks().forEach(track => {
          try {
            if (torchEnabled && track.applyConstraints) {
              track.applyConstraints({ advanced: [{ torch: false }] }).catch(() => {});
            }
            track.stop();
          } catch (trackErr) {
            console.warn('Error stopping camera track:', trackErr);
          }
        });
        videoRef.current.srcObject = null;
      }
    } catch (e) {
      console.warn('Error stopping video stream:', e);
    }
    setTorchEnabled(false);
    setIsScanning(false);
  }, [torchEnabled]);

  // Toggle flashlight / torch
  const toggleTorch = async () => {
    try {
      const stream = videoRef.current?.srcObject;
      if (!stream) return;
      const videoTrack = stream.getVideoTracks()[0];
      if (!videoTrack) return;

      const newTorchState = !torchEnabled;
      await videoTrack.applyConstraints({
        advanced: [{ torch: newTorchState }]
      });
      setTorchEnabled(newTorchState);
    } catch (err) {
      console.warn('Failed to toggle torch:', err);
    }
  };

  // Start scanner
  const startScanning = useCallback(async (deviceId = null) => {
    setIsLoading(true);
    setErrorMessage('');
    setErrorType('');
    scanLockRef.current = false;
    setLastScannedCode(null);

    // Stop any existing stream
    stopStream();

    // Check secure context (camera requires HTTPS or localhost)
    const isSecureContext = window.isSecureContext || 
      window.location.hostname === 'localhost' || 
      window.location.hostname === '127.0.0.1';

    if (!isSecureContext && window.location.protocol !== 'https:') {
      setIsLoading(false);
      setErrorType('https');
      setErrorMessage(
        'The camera only works on a secure (https://) page. Open EATGOOD over https, or type the barcode instead.'
      );
      return;
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setIsLoading(false);
      setErrorType('general');
      setErrorMessage('Your browser or device does not support camera video capture.');
      return;
    }

    try {
      // Configure specific 1D retail barcode hints (EAN-13, EAN-8, UPC-A, UPC-E)
      const hints = new Map();
      hints.set(DecodeHintType.POSSIBLE_FORMATS, [
        BarcodeFormat.EAN_13,
        BarcodeFormat.EAN_8,
        BarcodeFormat.UPC_A,
        BarcodeFormat.UPC_E,
        BarcodeFormat.UPC_EAN_EXTENSION
      ]);

      const reader = new BrowserMultiFormatReader(hints);
      readerRef.current = reader;

      // Enumerate video devices if not already done
      try {
        const devices = await BrowserMultiFormatReader.listVideoInputDevices();
        setVideoDevices(devices);
      } catch (devErr) {
        console.warn('Could not list video input devices:', devErr);
      }

      // Constraints: prefer rear environment camera
      const constraints = deviceId ? {
        video: { deviceId: { exact: deviceId } }
      } : {
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      };

      if (!videoRef.current) return;

      const controls = await reader.decodeFromConstraints(
        constraints,
        videoRef.current,
        (result) => {
          if (result && !scanLockRef.current) {
            const rawText = result.getText();
            if (rawText && rawText.trim()) {
              const cleaned = String(rawText).trim();
              const now = Date.now();
              // Prevent duplicate triggers for 2.5 seconds
              if (now - lastScannedTimeRef.current < 2500) {
                return;
              }

              // Validate that the detected code is a valid numeric string of standard length (8-14 digits)
              if (/^\d{8,14}$/.test(cleaned)) {
                scanLockRef.current = true;
                lastScannedTimeRef.current = now;
                setLastScannedCode(cleaned);
                triggerAudioBeep();
                
                // Callback to parent
                if (onScan) {
                  onScan(cleaned);
                }

                // Release lock after 2.5s
                setTimeout(() => {
                  scanLockRef.current = false;
                }, 2500);
              }
            }
          }
        }
      );

      controlsRef.current = controls;
      setIsScanning(true);

      // Check torch capabilities on the active video track
      setTimeout(() => {
        try {
          const stream = videoRef.current?.srcObject;
          if (stream) {
            const track = stream.getVideoTracks()[0];
            if (track && track.getCapabilities) {
              const caps = track.getCapabilities();
              if (caps.torch) {
                setTorchAvailable(true);
              }
            }
          }
        } catch (capErr) {
          console.warn('Could not read camera torch capability:', capErr);
        }
      }, 500);

      setIsLoading(false);
    } catch (err) {
      console.error('Failed to start barcode scanner:', err);
      setIsLoading(false);
      setIsScanning(false);
      const name = err.name || '';

      if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
        setErrorType('permission');
        setErrorMessage('Camera access was blocked. Allow the camera for this site in your browser settings (usually the icon next to the address), then try again — or type the barcode instead.');
      } else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
        setErrorType('not_found');
        setErrorMessage('No camera was found on this device. Type the barcode instead.');
      } else if (name === 'NotReadableError' || name === 'TrackStartError') {
        setErrorType('general');
        setErrorMessage('The camera is being used by another app or tab. Close it and try again.');
      } else {
        setErrorType('general');
        setErrorMessage('The camera could not be started. Try again, or type the barcode instead.');
      }
    }
  }, [stopStream, onScan]);

  // Handle camera switch (e.g., front vs back)
  const handleSwitchCamera = () => {
    if (videoDevices.length <= 1) return;
    const currentIndex = videoDevices.findIndex(d => d.deviceId === currentDeviceId);
    const nextIndex = (currentIndex + 1) % videoDevices.length;
    const nextDevice = videoDevices[nextIndex];
    setCurrentDeviceId(nextDevice.deviceId);
    startScanning(nextDevice.deviceId);
  };

  // Keep the latest callbacks in refs so the effect only re-runs when scanning is toggled,
  // and always releases the camera with the current stop function on unmount.
  const startRef = useRef(startScanning);
  const stopRef = useRef(stopStream);
  useEffect(() => {
    startRef.current = startScanning;
    stopRef.current = stopStream;
  }, [startScanning, stopStream]);

  useEffect(() => {
    if (isScanningActive) {
      startRef.current();
    }
    return () => {
      stopRef.current();
    };
  }, [isScanningActive]);

  return (
    <div 
      className="barcode-scanner-overlay"
      style={{
        position: 'relative',
        background: '#0d1f15',
        borderRadius: 14,
        overflow: 'hidden',
        color: '#fff',
        boxShadow: '0 8px 30px rgba(0,0,0,0.3)',
        maxWidth: 580,
        margin: '0 auto',
        border: '1px solid #2d4f3b'
      }}
    >
      {/* Top Header Toolbar */}
      <div 
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '12px 16px',
          background: 'rgba(13, 31, 21, 0.95)',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
          zIndex: 10,
          position: 'relative'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 10,
            height: 10,
            borderRadius: '50%',
            background: isLoading ? '#f59e0b' : (errorMessage ? '#ef4444' : (isScanning ? '#10b981' : '#6b7280')),
            boxShadow: `0 0 8px ${isLoading ? '#f59e0b' : (errorMessage ? '#ef4444' : (isScanning ? '#10b981' : '#6b7280'))}`
          }} />
          <span style={{ fontSize: '0.88rem', fontWeight: 700, letterSpacing: '0.02em' }}>
            {isLoading ? 'Starting Camera...' : (errorMessage ? 'Camera Offline' : (isScanning ? 'Live Barcode Scanner' : 'Scanner Paused'))}
          </span>
        </div>

        {/* Toolbar Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Start / Stop Toggle */}
          {!errorMessage && !isLoading && (
            <button
              type="button"
              onClick={isScanning ? stopStream : () => startScanning(currentDeviceId)}
              title={isScanning ? 'Stop / pause camera' : 'Start / resume scanning'}
              style={{
                background: isScanning ? 'rgba(239, 68, 68, 0.2)' : '#10b981',
                color: isScanning ? '#fca5a5' : '#fff',
                border: isScanning ? '1px solid rgba(239, 68, 68, 0.4)' : 'none',
                borderRadius: 8,
                padding: '6px 10px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              {isScanning ? <Pause size={14} /> : <Play size={14} />}
              <span>{isScanning ? 'Stop' : 'Start'}</span>
            </button>
          )}

          {/* Flashlight / Torch */}
          {torchAvailable && !errorMessage && !isLoading && isScanning && (
            <button
              type="button"
              onClick={toggleTorch}
              title={torchEnabled ? 'Turn torch off' : 'Turn torch on'}
              style={{
                background: torchEnabled ? '#f59e0b' : 'rgba(255,255,255,0.15)',
                color: torchEnabled ? '#000' : '#fff',
                border: 'none',
                borderRadius: 8,
                padding: '6px 10px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              {torchEnabled ? <ZapOff size={14} /> : <Zap size={14} />}
              <span>{torchEnabled ? 'Torch On' : 'Torch'}</span>
            </button>
          )}

          {/* Flip Camera */}
          {videoDevices.length > 1 && !errorMessage && !isLoading && (
            <button
              type="button"
              onClick={handleSwitchCamera}
              title="Switch camera"
              style={{
                background: 'rgba(255,255,255,0.15)',
                color: '#fff',
                border: 'none',
                borderRadius: 8,
                padding: '6px 10px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              <FlipHorizontal size={14} />
              <span>Flip</span>
            </button>
          )}

          {/* Close Scanner */}
          <button
            type="button"
            onClick={() => {
              stopStream();
              if (onClose) onClose();
            }}
            aria-label="Close camera scanner"
            style={{
              background: 'rgba(255,255,255,0.15)',
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              padding: 6,
              display: 'inline-flex',
              cursor: 'pointer'
            }}
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Viewport Frame */}
      <div 
        style={{
          position: 'relative',
          width: '100%',
          minHeight: 320,
          maxHeight: 460,
          background: '#000',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          overflow: 'hidden'
        }}
      >
        {/* Real Video Element */}
        <video
          ref={videoRef}
          playsInline
          muted
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            display: (errorMessage || !isScanning) ? 'none' : 'block'
          }}
        />

        {/* Viewfinder Target Reticle */}
        {!errorMessage && !isLoading && isScanning && (
          <div 
            className="barcode-viewfinder"
            style={{
              position: 'absolute',
              width: '78%',
              maxWidth: 320,
              height: 190,
              border: '2px solid rgba(16, 185, 129, 0.7)',
              borderRadius: 12,
              boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.5)',
              pointerEvents: 'none',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              padding: 8
            }}
          >
            {/* Viewfinder Reticle Corners */}
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <div style={{ width: 16, height: 16, borderTop: '3px solid #10b981', borderLeft: '3px solid #10b981' }} />
              <div style={{ width: 16, height: 16, borderTop: '3px solid #10b981', borderRight: '3px solid #10b981' }} />
            </div>

            {/* Laser Scanning Line Animation */}
            <div 
              style={{
                width: '100%',
                height: 2,
                background: 'linear-gradient(90deg, transparent, #ef4444, #10b981, transparent)',
                boxShadow: '0 0 8px #ef4444',
                animation: 'scannerLaser 2s ease-in-out infinite'
              }}
            />

            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <div style={{ width: 16, height: 16, borderBottom: '3px solid #10b981', borderLeft: '3px solid #10b981' }} />
              <div style={{ width: 16, height: 16, borderBottom: '3px solid #10b981', borderRight: '3px solid #10b981' }} />
            </div>
          </div>
        )}

        {/* Paused State */}
        {!isScanning && !isLoading && !errorMessage && (
          <div 
            style={{
              position: 'absolute',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 12,
              color: '#e5e7eb',
              padding: 24,
              textAlign: 'center'
            }}
          >
            <div style={{
              width: 52,
              height: 52,
              borderRadius: '50%',
              background: 'rgba(255,255,255,0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 6px'
            }}>
              <Pause size={24} color="#10b981" />
            </div>
            <div style={{ fontSize: '1rem', fontWeight: 700 }}>Scanner Paused</div>
            <p style={{ fontSize: '0.82rem', color: '#9ca3af', maxWidth: 280, margin: 0 }}>
              Camera stream stopped. Click below to resume scanning food barcodes.
            </p>
            <button
              type="button"
              onClick={() => startScanning(currentDeviceId)}
              className="btn-primary"
              style={{
                marginTop: 8,
                padding: '8px 20px',
                fontSize: '0.85rem',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                background: '#10b981'
              }}
            >
              <Play size={14} />
              <span>Resume Scanning</span>
            </button>
          </div>
        )}

        {/* Loading Spinner */}
        {isLoading && (
          <div 
            style={{
              position: 'absolute',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 12,
              color: '#e5e7eb',
              padding: 24,
              textAlign: 'center'
            }}
          >
            <RefreshCw size={32} className="spin" style={{ animation: 'spin 1s linear infinite', color: '#10b981' }} />
            <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>Requesting camera permission & sensor...</div>
            <div style={{ fontSize: '0.78rem', color: '#9ca3af', maxWidth: 280 }}>
              Prefers rear device camera. The barcode is decoded in your browser; only the number is sent to look the product up.
            </div>
          </div>
        )}

        {/* Error State Display */}
        {errorMessage && !isLoading && (
          <div 
            style={{
              position: 'absolute',
              padding: 24,
              textAlign: 'center',
              color: '#fff',
              maxWidth: 420
            }}
          >
            <div style={{
              width: 52,
              height: 52,
              borderRadius: '50%',
              background: 'rgba(239, 68, 68, 0.2)',
              border: '1px solid #ef4444',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 12px'
            }}>
              <AlertTriangle size={26} color="#ef4444" />
            </div>

            <div style={{ fontSize: '1rem', fontWeight: 700, marginBottom: 6 }}>
              {errorType === 'permission' ? 'Camera Permission Denied' : 
               errorType === 'https' ? 'Secure Context Required' : 'Camera Unavailable'}
            </div>

            <p style={{ fontSize: '0.82rem', color: '#d1d5db', lineHeight: 1.4, marginBottom: 16 }}>
              {errorMessage}
            </p>

            <div style={{ display: 'flex', justifyContent: 'center', gap: 10, flexWrap: 'wrap' }}>
              <button
                type="button"
                onClick={() => startScanning(currentDeviceId)}
                className="btn-primary"
                style={{
                  padding: '8px 16px',
                  fontSize: '0.82rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  background: '#10b981'
                }}
              >
                <RefreshCw size={14} />
                <span>Retry Camera</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  stopStream();
                  if (onManualEntry) {
                    onManualEntry();
                  } else if (onClose) {
                    onClose();
                  }
                }}
                className="btn-secondary"
                style={{
                  padding: '8px 16px',
                  fontSize: '0.82rem',
                  background: 'rgba(255,255,255,0.1)',
                  color: '#fff',
                  border: '1px solid rgba(255,255,255,0.2)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6
                }}
              >
                <Keyboard size={14} />
                <span>Enter Barcode Manually</span>
              </button>
            </div>
          </div>
        )}

        {/* Last Scanned Feedback Toast */}
        {lastScannedCode && (
          <div 
            style={{
              position: 'absolute',
              bottom: 16,
              background: '#047857',
              color: '#fff',
              padding: '6px 14px',
              borderRadius: 20,
              fontSize: '0.82rem',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
              animation: 'fadeIn 0.2s ease-out'
            }}
          >
            <CheckCircle2 size={16} />
            <span>Barcode detected: {lastScannedCode}</span>
          </div>
        )}
      </div>

      {/* Bottom Instructions Footer */}
      <div 
        style={{
          padding: '12px 16px',
          background: 'rgba(13, 31, 21, 0.95)',
          borderTop: '1px solid rgba(255,255,255,0.1)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 8,
          fontSize: '0.78rem',
          color: '#9ca3af'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Shield size={14} color="#10b981" />
          <span>Local retail barcode detection (EAN-13, EAN-8, UPC-A, UPC-E)</span>
        </div>

        <button
          type="button"
          onClick={() => {
            stopStream();
            if (onClose) onClose();
          }}
          style={{
            background: 'none',
            border: 'none',
            color: '#10b981',
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: '0.78rem',
            padding: 0
          }}
        >
          Cancel & Close
        </button>
      </div>

      <style>{`
        @keyframes scannerLaser {
          0% { transform: translateY(0); opacity: 0.8; }
          50% { transform: translateY(165px); opacity: 1; }
          100% { transform: translateY(0); opacity: 0.8; }
        }
      `}</style>
    </div>
  );
}
