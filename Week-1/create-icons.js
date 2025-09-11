// Simple script to create icon files
// This creates placeholder icon files that can be replaced with actual PNG files

const fs = require('fs');
const path = require('path');

// Create icons directory if it doesn't exist
const iconsDir = path.join(__dirname, 'icons');
if (!fs.existsSync(iconsDir)) {
    fs.mkdirSync(iconsDir, { recursive: true });
}

// Create a simple SVG icon
const svgIcon = `<svg width="128" height="128" viewBox="0 0 128 128" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="64" cy="64" r="60" fill="#2563eb" stroke="#1e40af" stroke-width="4"/>
  <rect x="32" y="24" width="48" height="64" rx="4" fill="white"/>
  <rect x="40" y="36" width="32" height="3" rx="1.5" fill="#2563eb"/>
  <rect x="40" y="44" width="28" height="3" rx="1.5" fill="#2563eb"/>
  <rect x="40" y="52" width="32" height="3" rx="1.5" fill="#2563eb"/>
  <rect x="40" y="60" width="24" height="3" rx="1.5" fill="#2563eb"/>
  <rect x="40" y="68" width="30" height="3" rx="1.5" fill="#2563eb"/>
  <circle cx="88" cy="40" r="6" fill="#fbbf24"/>
  <path d="M88 32L90 36L94 36L91 39L92 43L88 40L84 43L85 39L82 36L86 36L88 32Z" fill="#f59e0b"/>
  <circle cx="100" cy="100" r="12" fill="none" stroke="white" stroke-width="3"/>
  <line x1="108" y1="108" x2="116" y2="116" stroke="white" stroke-width="3" stroke-linecap="round"/>
  <circle cx="24" cy="88" r="2" fill="#fbbf24"/>
  <circle cx="32" cy="88" r="2" fill="#fbbf24"/>
  <circle cx="40" cy="88" r="2" fill="#fbbf24"/>
</svg>`;

// Save SVG icon
fs.writeFileSync(path.join(iconsDir, 'icon.svg'), svgIcon);

// Create placeholder files for PNG icons
const sizes = [16, 32, 48, 128];
sizes.forEach(size => {
    const placeholderContent = `# Placeholder for ${size}x${size} icon
# This file should be replaced with an actual PNG icon
# You can use the generate-icons.html file to create proper PNG icons
# Or use any image editor to create ${size}x${size} PNG files
`;
    fs.writeFileSync(path.join(iconsDir, `icon${size}.png`), placeholderContent);
});

console.log('✅ Icon files created successfully!');
console.log('📁 Check the icons/ folder for the generated files');
console.log('🎨 Use generate-icons.html to create proper PNG icons');
console.log('📝 Or replace the placeholder files with actual PNG icons');
