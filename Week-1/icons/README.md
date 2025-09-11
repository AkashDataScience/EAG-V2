# Extension Icons

This folder should contain the following icon files:

- `icon16.png` - 16x16 pixels (toolbar icon)
- `icon32.png` - 32x32 pixels (Windows)
- `icon48.png` - 48x48 pixels (extension management page)
- `icon128.png` - 128x128 pixels (Chrome Web Store)

## 🎨 Creating Icons

### Method 1: Use the Icon Generator (Recommended)
1. Open `generate-icons.html` in your browser
2. Click the download buttons for each size
3. Save the files in this `icons/` folder
4. Reload your Chrome extension

### Method 2: Manual Creation
You can create these icons using any image editor. The icons should:

1. Be in PNG format
2. Have transparent backgrounds
3. Be clearly visible at small sizes
4. Represent the extension's purpose (document/research theme)

### Method 3: Online Generators
- Use online icon generators like favicon.io
- Upload the provided `icon.svg` file
- Generate different sizes

## 🎯 Icon Design

The current icon design includes:
- **Blue circular background** (#2563eb) - Professional, trustworthy
- **White document** - Represents papers/documents
- **Text lines** - Shows content analysis
- **Golden sparkle** - Represents AI/magic
- **Magnifying glass** - Represents research/analysis
- **Processing dots** - Shows AI processing

## 🚀 Quick Setup

1. **Run the generator**: Open `generate-icons.html` in your browser
2. **Download icons**: Click all four download buttons
3. **Save files**: Place them in this `icons/` folder
4. **Reload extension**: Refresh your Chrome extension

## 📝 File Structure

```
icons/
├── icon16.png    # 16x16 pixels
├── icon32.png    # 32x32 pixels  
├── icon48.png    # 48x48 pixels
├── icon128.png   # 128x128 pixels
├── icon.svg      # Source SVG file
└── README.md     # This file
```

## ✅ Verification

After adding the icons:
1. Reload the extension in Chrome
2. Check that the icon appears in the toolbar
3. Verify the icon shows in the extensions page
4. Test that the popup opens when clicking the icon
