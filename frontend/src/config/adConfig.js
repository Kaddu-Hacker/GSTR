/**
 * Advertisement Configuration
 * 
 * How to use:
 * 1. Get your ad code from Google AdSense or Propeller Ads
 * 2. Paste the entire script/code into the 'code' field
 * 3. Set 'enabled' to true to activate the ad
 * 4. Save and restart the frontend
 * 
 * Supported Ad Networks:
 * - Google AdSense
 * - Propeller Ads
 * - Any other ad network that provides HTML/JavaScript code
 */

export const adConfig = {
  // Header Banner Ad (728x90 or responsive)
  headerBanner: {
    id: 'header-banner-ad',
    enabled: false,
    code: `
      <!-- Replace this comment with your Google AdSense or Propeller Ads code -->
      <!-- Example for AdSense:
      <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXX"
           crossorigin="anonymous"></script>
      <ins class="adsbygoogle"
           style="display:block"
           data-ad-client="ca-pub-XXXXXXXXXX"
           data-ad-slot="XXXXXXXXXX"
           data-ad-format="auto"
           data-full-width-responsive="true"></ins>
      <script>
           (adsbygoogle = window.adsbygoogle || []).push({});
      </script>
      -->
    `,
    description: 'Banner ad displayed below the header'
  },

  // Sidebar Ad (300x250 or 300x600)
  sidebar: {
    id: 'sidebar-ad',
    enabled: false,
    code: `
      <!-- Replace this comment with your Google AdSense or Propeller Ads code -->
    `,
    description: 'Ad displayed in the right sidebar'
  },

  // In-Content Ad 1 (Between upload and preview sections)
  inContent1: {
    id: 'in-content-ad-1',
    enabled: false,
    code: `
      <!-- Replace this comment with your Google AdSense or Propeller Ads code -->
    `,
    description: 'Ad displayed between upload and preview sections'
  },

  // In-Content Ad 2 (Between preview and download sections)
  inContent2: {
    id: 'in-content-ad-2',
    enabled: false,
    code: `
      <!-- Replace this comment with your Google AdSense or Propeller Ads code -->
    `,
    description: 'Ad displayed between preview and download sections'
  },

  // Footer Banner Ad (728x90 or responsive)
  footerBanner: {
    id: 'footer-banner-ad',
    enabled: false,
    code: `
      <!-- Replace this comment with your Google AdSense or Propeller Ads code -->
    `,
    description: 'Banner ad displayed above the footer'
  },

  // Global Ad Settings
  global: {
    // Show placeholder when ads are disabled (for development/testing)
    showPlaceholder: true,
    
    // Ad refresh interval in seconds (0 = no refresh)
    refreshInterval: 0,
    
    // Responsive breakpoints
    breakpoints: {
      mobile: 768,
      tablet: 1024,
      desktop: 1280
    }
  }
};

export default adConfig;
