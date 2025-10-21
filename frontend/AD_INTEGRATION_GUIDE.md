# Advertisement Integration Guide

This guide explains how to integrate Google AdSense and Propeller Ads into your GST Filing Automation application.

## 📋 Table of Contents
1. [Overview](#overview)
2. [Ad Placements](#ad-placements)
3. [Configuration](#configuration)
4. [Google AdSense Integration](#google-adsense-integration)
5. [Propeller Ads Integration](#propeller-ads-integration)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

The application uses a **component-based ad system** with the following features:
- **5 strategic ad placements** (header, sidebar, in-content x2, footer)
- **Easy configuration** via config file
- **Multiple ad networks** supported (AdSense, Propeller, etc.)
- **Responsive design** for mobile, tablet, and desktop
- **Development mode** with placeholders for testing

---

## 📍 Ad Placements

### 1. Header Banner Ad
- **Location:** Below the main header
- **Recommended Size:** 728x90 (Leaderboard) or Responsive
- **Config Key:** `headerBanner`

### 2. Sidebar Ad
- **Location:** Right sidebar (sticky on desktop)
- **Recommended Size:** 300x250 (Medium Rectangle) or 300x600 (Half Page)
- **Config Key:** `sidebar`
- **Note:** Only visible on desktop (hidden on mobile/tablet)

### 3. In-Content Ad 1
- **Location:** Between file upload and preview sections
- **Recommended Size:** Responsive or 728x90
- **Config Key:** `inContent1`

### 4. In-Content Ad 2
- **Location:** Between preview and download sections
- **Recommended Size:** Responsive or 728x90
- **Config Key:** `inContent2`

### 5. Footer Banner Ad
- **Location:** Above the footer
- **Recommended Size:** 728x90 (Leaderboard) or Responsive
- **Config Key:** `footerBanner`

---

## ⚙️ Configuration

All ad configurations are stored in: `/app/frontend/src/config/adConfig.js`

### Basic Structure

```javascript
export const adConfig = {
  headerBanner: {
    id: 'header-banner-ad',
    enabled: false,  // Set to true to activate
    code: `<!-- Your ad code here -->`,
    description: 'Banner ad displayed below the header'
  },
  // ... other ad slots
};
```

### Steps to Configure an Ad

1. Open `/app/frontend/src/config/adConfig.js`
2. Find the ad slot you want to configure (e.g., `headerBanner`)
3. Replace the `code` field with your ad network's code
4. Set `enabled: true`
5. Save the file
6. Restart the frontend: `sudo supervisorctl restart frontend`

---

## 🟢 Google AdSense Integration

### Step 1: Get Your AdSense Code

1. Log in to [Google AdSense](https://www.google.com/adsense/)
2. Go to **Ads** → **By ad unit** → **Display ads**
3. Create a new ad unit or select an existing one
4. Copy the generated code

### Step 2: Add to Configuration

**Example AdSense Code:**

```javascript
headerBanner: {
  id: 'header-banner-ad',
  enabled: true,  // ⚠️ Important: Set to true
  code: `
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
  `,
  description: 'Banner ad displayed below the header'
}
```

### Step 3: Add AdSense Head Script (One-Time Setup)

Add the following to `/app/frontend/public/index.html` in the `<head>` section:

```html
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXX"
     crossorigin="anonymous"></script>
```

Replace `XXXXXXXXXX` with your AdSense publisher ID.

---

## 🔵 Propeller Ads Integration

### Step 1: Get Your Propeller Code

1. Log in to [Propeller Ads](https://propellerads.com/)
2. Go to **Websites** → **New Zone**
3. Select ad format (Banner, Interstitial, etc.)
4. Copy the generated code

### Step 2: Add to Configuration

**Example Propeller Banner Code:**

```javascript
sidebar: {
  id: 'sidebar-ad',
  enabled: true,  // ⚠️ Important: Set to true
  code: `
    <script type="text/javascript">
      atOptions = {
        'key' : 'your-propeller-key-here',
        'format' : 'iframe',
        'height' : 600,
        'width' : 300,
        'params' : {}
      };
    </script>
    <script type="text/javascript" src="//www.topcreativeformat.com/your-propeller-key-here/invoke.js"></script>
  `,
  description: 'Ad displayed in the right sidebar'
}
```

**Example Propeller Push Notification (Optional):**

Add to `/app/frontend/public/index.html` before closing `</body>`:

```html
<script type="text/javascript">
  (function(d,z,s){s.src='https://'+d+'/400/'+z;try{(document.body||document.documentElement).appendChild(s)}catch(e){}})
  ('domain.com','your-zone-id',document.createElement('script'))
</script>
```

---

## 🧪 Testing

### Development Mode

By default, the app shows **ad placeholders** when ads are disabled or not configured. This helps you visualize where ads will appear.

To hide placeholders, edit `/app/frontend/src/config/adConfig.js`:

```javascript
global: {
  showPlaceholder: false,  // Set to false to hide placeholders
  // ... other settings
}
```

### Testing Checklist

- [ ] Ads appear in correct positions
- [ ] Ads load without errors (check browser console)
- [ ] Ads are responsive on mobile/tablet/desktop
- [ ] Multiple ads don't conflict with each other
- [ ] Page performance is acceptable
- [ ] Ads comply with ad network policies

### Browser Console Testing

1. Open browser DevTools (F12)
2. Go to Console tab
3. Check for any errors related to ad loading
4. Common errors:
   - `adsbygoogle is not defined` → AdSense script not loaded
   - CORS errors → Check crossorigin attribute
   - 404 errors → Check ad script URLs

---

## 🔧 Troubleshooting

### Ads Not Showing

**Problem:** Ads don't appear even after configuration

**Solutions:**
1. Verify `enabled: true` in config
2. Check browser console for errors
3. Clear browser cache and reload
4. Verify ad network approval (new sites may need approval)
5. Check if ad blockers are enabled (disable for testing)
6. Restart frontend: `sudo supervisorctl restart frontend`

### AdSense Blank Ads

**Problem:** AdSense shows blank space

**Solutions:**
1. Wait 24-48 hours after initial setup (AdSense needs time)
2. Verify site is approved in AdSense dashboard
3. Check if domain is added to AdSense
4. Ensure sufficient content on pages

### Propeller Ads Not Loading

**Problem:** Propeller ads don't load

**Solutions:**
1. Verify zone ID is correct
2. Check if website is approved
3. Ensure script URLs are correct
4. Check for JavaScript errors

### Layout Issues

**Problem:** Ads break the layout

**Solutions:**
1. Adjust ad sizes in config
2. Use responsive ad units
3. Modify CSS in `/app/frontend/src/App.css`
4. Test on different screen sizes

### Multiple Ad Networks

**Problem:** Want to use both AdSense and Propeller

**Solution:**
You can use different networks for different slots:
```javascript
headerBanner: {
  enabled: true,
  code: `<!-- Google AdSense code -->`
},
sidebar: {
  enabled: true,
  code: `<!-- Propeller Ads code -->`
}
```

---

## 📝 Best Practices

1. **Don't overload with ads** - Too many ads hurt user experience
2. **Use responsive ad units** - Better mobile experience
3. **Test thoroughly** - Check all devices and browsers
4. **Monitor performance** - Track revenue and user metrics
5. **Comply with policies** - Follow ad network guidelines
6. **Optimize placement** - Test different positions for better CTR
7. **Regular updates** - Keep ad codes and scripts updated

---

## 🚀 Quick Start Example

Here's a complete example to get you started quickly:

1. **Edit** `/app/frontend/src/config/adConfig.js`:

```javascript
export const adConfig = {
  headerBanner: {
    id: 'header-banner-ad',
    enabled: true,
    code: `
      <!-- Your Google AdSense code here -->
      <ins class="adsbygoogle"
           style="display:block"
           data-ad-client="ca-pub-XXXXXXXXXX"
           data-ad-slot="1234567890"
           data-ad-format="auto"
           data-full-width-responsive="true"></ins>
      <script>
           (adsbygoogle = window.adsbygoogle || []).push({});
      </script>
    `,
    description: 'Banner ad displayed below the header'
  },
  
  sidebar: {
    id: 'sidebar-ad',
    enabled: true,
    code: `
      <!-- Your Propeller Ads code here -->
      <script type="text/javascript">
        atOptions = {
          'key' : 'your-key-here',
          'format' : 'iframe',
          'height' : 600,
          'width' : 300,
          'params' : {}
        };
      </script>
      <script type="text/javascript" src="//www.topcreativeformat.com/your-key/invoke.js"></script>
    `,
    description: 'Ad displayed in the right sidebar'
  }
  // ... configure other slots as needed
};
```

2. **Save** the file

3. **Restart** frontend:
```bash
sudo supervisorctl restart frontend
```

4. **Test** in browser

---

## 📞 Support

If you encounter issues:
1. Check this guide first
2. Review browser console for errors
3. Verify ad network dashboard for approval status
4. Test with ad blockers disabled

---

## 📄 File Structure

```
/app/frontend/
├── src/
│   ├── config/
│   │   └── adConfig.js          # Main ad configuration
│   ├── components/
│   │   └── AdSpace.js           # Reusable ad component
│   ├── App.js                    # Main app with ad placements
│   └── App.css                   # Styling including ad styles
└── AD_INTEGRATION_GUIDE.md       # This guide
```

---

**Last Updated:** 2025

**Need Help?** Refer to:
- [Google AdSense Help Center](https://support.google.com/adsense/)
- [Propeller Ads Support](https://propellerads.com/help/)
