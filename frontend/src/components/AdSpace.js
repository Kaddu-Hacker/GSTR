import React, { useEffect, useRef } from 'react';
import { adConfig } from '../config/adConfig';

/**
 * AdSpace Component
 * 
 * A reusable component for displaying advertisements
 * Supports Google AdSense, Propeller Ads, and other ad networks
 * 
 * @param {string} adSlot - The ad slot ID from adConfig (e.g., 'headerBanner', 'sidebar')
 * @param {string} className - Additional CSS classes
 */
const AdSpace = ({ adSlot, className = '' }) => {
  const adRef = useRef(null);
  const adData = adConfig[adSlot];

  useEffect(() => {
    // If ad is enabled and has code, inject it
    if (adData?.enabled && adData?.code && adRef.current) {
      try {
        // Clear any existing content
        adRef.current.innerHTML = adData.code;

        // Execute any inline scripts
        const scripts = adRef.current.getElementsByTagName('script');
        for (let i = 0; i < scripts.length; i++) {
          const script = scripts[i];
          const newScript = document.createElement('script');
          
          // Copy attributes
          Array.from(script.attributes).forEach(attr => {
            newScript.setAttribute(attr.name, attr.value);
          });
          
          // Copy content
          if (script.innerHTML) {
            newScript.innerHTML = script.innerHTML;
          }
          
          // Replace old script with new one to execute it
          script.parentNode.replaceChild(newScript, script);
        }
      } catch (error) {
        console.error(`Error loading ad for slot ${adSlot}:`, error);
      }
    }
  }, [adSlot, adData]);

  // If ad is not configured or disabled
  if (!adData || !adData.enabled) {
    // Show placeholder in development mode
    if (adConfig.global?.showPlaceholder) {
      return (
        <div 
          className={`ad-placeholder border-2 border-dashed border-gray-700 rounded-lg p-4 text-center bg-gray-800/30 ${className}`}
          data-ad-slot={adSlot}
        >
          <div className="text-gray-500 text-sm">
            <p className="font-semibold mb-1">Ad Space: {adSlot}</p>
            <p className="text-xs">{adData?.description || 'Advertisement placeholder'}</p>
            <p className="text-xs mt-2 text-gray-600">
              Configure in: <code className="text-purple-400">src/config/adConfig.js</code>
            </p>
          </div>
        </div>
      );
    }
    return null;
  }

  // Render the ad container
  return (
    <div 
      ref={adRef}
      className={`ad-container ${className}`}
      data-ad-slot={adSlot}
      data-ad-id={adData.id}
    />
  );
};

export default AdSpace;
