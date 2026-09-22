'use client'

import { useEffect } from 'react'

/**
 * Registers the service worker on mount. Required for the app to be
 * installable ("Add to Home Screen") and for push notifications to work —
 * see public/sw.js for what it actually does.
 */
export default function ServiceWorkerRegister() {
  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch((err) => {
        console.error('Service worker registration failed:', err)
      })
    }
  }, [])

  return null
}
