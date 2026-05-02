# Theme System Documentation

## Overview

The face recognition application includes a comprehensive theme system that supports light and dark modes. The theme system is built using Angular signals for reactive state management and Tailwind CSS for styling.

## Features

- **Light and Dark Modes**: Toggle between two carefully designed themes
- **Automatic Persistence**: Theme preference is saved to localStorage
- **System Preference Detection**: Respects user's system theme preference
- **Fast Switching**: Theme changes apply within 100ms
- **WCAG AA Compliant**: Both themes meet accessibility color contrast standards
- **Responsive**: Works seamlessly across all device sizes

## Using the Theme System

### Theme Toggle Component

The theme toggle button is located in the main navigation bar. It displays:
- **Sun icon** when in dark mode (click to switch to light)
- **Moon icon** when in light mode (click to switch to dark)

### Keyboard Accessibility

The theme toggle is fully keyboard accessible:
- **Tab**: Navigate to the theme toggle button
- **Enter/Space**: Toggle the theme
- **Screen readers**: Announces "Switch to light mode" or "Switch to dark mode"

## Technical Implementation

### Theme Service

The theme system is powered by `ThemeService` located in `src/app/services/theme.service.ts`.

**Key Features:**
- Signal-based reactive state management
- Automatic theme application via effects
- localStorage persistence
- System preference detection

**API:**

```typescript
class ThemeService {
  // Read-only signals
  readonly currentTheme: Signal<Theme>;  // 'light' | 'dark'
  readonly isDark: Signal<boolean>;      // computed from currentTheme
  
  // Methods
  toggleTheme(): void;                   // Switch between themes
  setTheme(theme: Theme): void;          // Set specific theme
}
```

**Usage Example:**

```typescript
import { inject } from '@angular/core';
import { ThemeService } from './services/theme.service';

export class MyComponent {
  private themeService = inject(ThemeService);
  
  // Access current theme
  currentTheme = this.themeService.currentTheme;
  isDark = this.themeService.isDark;
  
  // Toggle theme
  toggleTheme() {
    this.themeService.toggleTheme();
  }
}
```

### Theme Initialization

On application startup, the theme is initialized in this order:

1. **Check localStorage**: If a theme preference exists, use it
2. **Check system preference**: If no saved preference, detect system theme using `prefers-color-scheme`
3. **Default to light**: If neither exists, default to light theme

### Theme Application

When a theme is set:

1. The theme signal is updated
2. An effect automatically applies the theme class to `document.documentElement`
3. The preference is saved to localStorage
4. All components using theme-aware Tailwind classes update automatically

## Tailwind CSS Configuration

### Dark Mode Strategy

The theme system uses Tailwind's class-based dark mode strategy:

```javascript
// tailwind.config.js
module.exports = {
  darkMode: 'class',  // Use .dark class on html element
  // ...
}
```

### CSS Custom Properties

Theme colors are defined using CSS custom properties for maximum flexibility:

```css
/* src/styles.css */
@layer base {
  :root {
    /* Light theme colors */
    --color-background: 255 255 255;
    --color-foreground: 15 23 42;
    --color-card: 248 250 252;
    --color-card-foreground: 15 23 42;
    --color-primary: 59 130 246;
    --color-primary-foreground: 255 255 255;
    --color-border: 226 232 240;
    --color-input: 226 232 240;
    --color-ring: 59 130 246;
  }
  
  .dark {
    /* Dark theme colors */
    --color-background: 15 23 42;
    --color-foreground: 248 250 252;
    --color-card: 30 41 59;
    --color-card-foreground: 248 250 252;
    --color-primary: 96 165 250;
    --color-primary-foreground: 15 23 42;
    --color-border: 51 65 85;
    --color-input: 51 65 85;
    --color-ring: 96 165 250;
  }
}
```

### Using Theme Colors in Components

**Tailwind Utility Classes:**

```html
<!-- Background colors -->
<div class="bg-white dark:bg-slate-800">
  <!-- Content -->
</div>

<!-- Text colors -->
<p class="text-slate-900 dark:text-slate-100">
  Text content
</p>

<!-- Border colors -->
<div class="border border-slate-200 dark:border-slate-700">
  <!-- Content -->
</div>

<!-- Hover states -->
<button class="hover:bg-slate-100 dark:hover:bg-slate-800">
  Button
</button>
```

**Component Classes:**

```css
@layer components {
  .btn-primary {
    @apply bg-primary-600 text-white px-4 py-2 rounded-lg 
           hover:bg-primary-700 transition-colors duration-200 
           focus:outline-none focus:ring-2 focus:ring-primary-500 
           focus:ring-offset-2 dark:bg-primary-500 dark:hover:bg-primary-600;
  }
  
  .card {
    @apply bg-white dark:bg-slate-800 rounded-lg shadow-md p-6 
           border border-slate-200 dark:border-slate-700;
  }
}
```

## Customizing Themes

### Changing Theme Colors

To customize theme colors, edit `src/styles.css`:

1. **Locate the color definitions** in the `:root` and `.dark` selectors
2. **Update the RGB values** (format: `R G B` without commas)
3. **Rebuild the application** to apply changes

**Example - Changing Primary Color:**

```css
:root {
  --color-primary: 16 185 129;  /* Green instead of blue */
}

.dark {
  --color-primary: 52 211 153;  /* Lighter green for dark mode */
}
```

### Adding New Theme Colors

1. **Define the color** in both `:root` and `.dark`:

```css
:root {
  --color-accent: 236 72 153;  /* Pink */
}

.dark {
  --color-accent: 244 114 182;  /* Lighter pink */
}
```

2. **Extend Tailwind configuration** (optional, for utility classes):

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        accent: {
          DEFAULT: 'rgb(var(--color-accent))',
        },
      },
    },
  },
}
```

3. **Use in components**:

```html
<div class="bg-accent text-white">
  Accent colored element
</div>
```

### Creating Additional Themes

To add more themes (e.g., high contrast, colorblind-friendly):

1. **Update ThemeService** to support new theme types:

```typescript
export type Theme = 'light' | 'dark' | 'high-contrast';
```

2. **Add CSS for new theme**:

```css
.high-contrast {
  --color-background: 0 0 0;
  --color-foreground: 255 255 255;
  --color-primary: 255 255 0;
  /* ... more colors */
}
```

3. **Update theme toggle** to cycle through all themes

## Accessibility

### Color Contrast

Both themes meet WCAG 2.1 Level AA color contrast requirements:

- **Normal text**: Minimum 4.5:1 contrast ratio
- **Large text**: Minimum 3:1 contrast ratio
- **UI components**: Minimum 3:1 contrast ratio

### Testing Color Contrast

Use browser DevTools or online tools to verify contrast:

```bash
# Install axe-core for automated testing
npm install -D @axe-core/cli

# Run accessibility audit
axe http://localhost:4200 --tags wcag2aa
```

### Motion Preferences

The theme system respects user motion preferences:

```css
/* Disable transitions for users who prefer reduced motion */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

## Performance

### Theme Switch Performance

The theme system is optimized for fast switching:

- **Target**: <100ms from click to visual update
- **Implementation**: CSS class toggle on `document.documentElement`
- **No re-renders**: Components don't re-render, only CSS classes change

### Bundle Size Impact

The theme system adds minimal overhead:

- **ThemeService**: ~2KB
- **ThemeToggleComponent**: ~1KB
- **CSS custom properties**: ~1KB
- **Total**: ~4KB (gzipped)

## Browser Support

The theme system works in all modern browsers:

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

**Required Features:**
- CSS custom properties (CSS variables)
- `prefers-color-scheme` media query
- localStorage API

## Troubleshooting

### Theme Not Persisting

**Problem**: Theme resets to default on page reload

**Solution**:
1. Check browser localStorage is enabled
2. Check for localStorage quota errors in console
3. Verify no browser extensions are clearing localStorage

### Theme Not Applying

**Problem**: Theme toggle works but colors don't change

**Solution**:
1. Check that `.dark` class is added to `<html>` element
2. Verify Tailwind CSS is properly configured with `darkMode: 'class'`
3. Check that components use `dark:` variants in class names
4. Clear browser cache and rebuild application

### System Preference Not Detected

**Problem**: App doesn't respect system theme preference

**Solution**:
1. Verify browser supports `prefers-color-scheme` media query
2. Check that no theme preference is saved in localStorage (clear it to test)
3. Verify system theme is actually set (check OS settings)

### Performance Issues

**Problem**: Theme switching is slow or causes lag

**Solution**:
1. Check for excessive DOM elements (>1000)
2. Verify no JavaScript-based theme switching (should be CSS-only)
3. Check for expensive CSS selectors or transitions
4. Use Chrome DevTools Performance tab to profile

## Best Practices

### For Developers

1. **Always use Tailwind dark variants**: `dark:bg-slate-800` instead of custom CSS
2. **Test both themes**: Verify all components in light and dark modes
3. **Use semantic color names**: `bg-card` instead of `bg-white`
4. **Respect motion preferences**: Use `transition-colors` for theme changes
5. **Test accessibility**: Verify color contrast in both themes

### For Designers

1. **Design for both themes**: Create mockups for light and dark modes
2. **Maintain contrast**: Ensure 4.5:1 ratio for normal text
3. **Use consistent colors**: Stick to the defined color palette
4. **Test with real users**: Get feedback on theme preferences
5. **Consider colorblind users**: Don't rely on color alone to convey information

## Future Enhancements

Potential improvements to the theme system:

1. **More themes**: High contrast, colorblind-friendly, custom themes
2. **Theme customization UI**: Allow users to create custom color schemes
3. **Scheduled themes**: Auto-switch based on time of day
4. **Per-component themes**: Different themes for different sections
5. **Theme preview**: Preview theme before applying
6. **Theme sharing**: Export/import custom themes

## References

- [Tailwind CSS Dark Mode](https://tailwindcss.com/docs/dark-mode)
- [Angular Signals](https://angular.dev/guide/signals)
- [WCAG Color Contrast](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)
- [prefers-color-scheme](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-color-scheme)
- [CSS Custom Properties](https://developer.mozilla.org/en-US/docs/Web/CSS/--*)

