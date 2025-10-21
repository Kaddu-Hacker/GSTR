# 🚀 Quick Ad Setup Guide

## ⚡ Fast Setup (5 Minutes)

### Step 1: Get Your Ad Codes
- **Google AdSense**: Login → Ads → Create Ad Unit → Copy Code
- **Propeller Ads**: Login → New Zone → Select Format → Copy Code

### Step 2: Edit Configuration File
Open: `/app/frontend/src/config/adConfig.js`

### Step 3: Paste Your Code
```javascript
headerBanner: {
  id: 'header-banner-ad',
  enabled: true,  // ⚠️ CHANGE THIS TO TRUE!
  code: `
    <!-- PASTE YOUR AD CODE HERE -->
  `,
  description: 'Banner ad displayed below the header'
}
```

### Step 4: Save & Restart
```bash
sudo supervisorctl restart frontend
```

### Step 5: Test
Visit your site and verify ads are showing!

---

## 📍 Available Ad Slots

| Slot | Location | Size | Config Key |
|------|----------|------|------------|
| **Header Banner** | Below header | 728x90 or responsive | `headerBanner` |
| **Sidebar** | Right side (desktop only) | 300x250 or 300x600 | `sidebar` |
| **In-Content 1** | After upload section | Responsive | `inContent1` |
| **In-Content 2** | After preview section | Responsive | `inContent2` |
| **Footer Banner** | Above footer | 728x90 or responsive | `footerBanner` |

---

## 📝 Example: Google AdSense

```javascript
headerBanner: {
  id: 'header-banner-ad',
  enabled: true,
  code: `
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXX"
         crossorigin="anonymous"></script>
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
}
```

---

## 📝 Example: Propeller Ads

```javascript
sidebar: {
  id: 'sidebar-ad',
  enabled: true,
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
    <script type="text/javascript" src="//www.topcreativeformat.com/your-key/invoke.js"></script>
  `,
  description: 'Ad displayed in the right sidebar'
}
```

---

## 🔧 Troubleshooting

### Ads Not Showing?
1. ✅ Check `enabled: true` in config
2. ✅ Restart frontend: `sudo supervisorctl restart frontend`
3. ✅ Clear browser cache
4. ✅ Disable ad blocker for testing
5. ✅ Check browser console for errors (F12)

### Want to Hide Placeholders?
In `adConfig.js`, set:
```javascript
global: {
  showPlaceholder: false
}
```

---

## 📚 Full Documentation
See: `/app/frontend/AD_INTEGRATION_GUIDE.md` for complete guide

---

## ✅ Checklist

- [ ] Got ad codes from Google AdSense / Propeller Ads
- [ ] Pasted codes in `/app/frontend/src/config/adConfig.js`
- [ ] Set `enabled: true` for each ad slot
- [ ] Restarted frontend: `sudo supervisorctl restart frontend`
- [ ] Tested on browser with ad blocker disabled
- [ ] Verified all ad placements working
- [ ] Monitored revenue in ad network dashboard

---

**Need Help?** Check the full guide at `/app/frontend/AD_INTEGRATION_GUIDE.md`
