---
name: motion-framer
description: Modern animation library for React and JavaScript. Create smooth, production-ready animations with motion components, variants, gestures (hover/tap/drag), layout animations, AnimatePresence exit animations, spring physics, and scroll-based effects. Use when building interactive UI components, micro-interactions, page transitions, or complex animation sequences.
---

# Motion & Framer Motion

## Overview

Motion (formerly Framer Motion) is a production-ready animation library for React and JavaScript that enables declarative, performant animations with minimal code. It provides `motion` components that wrap HTML elements with animation superpowers, supports gesture recognition (hover, tap, drag, focus), and includes advanced features like layout animations, exit animations, and spring physics.

**When to use this skill:**
- Building interactive UI components (buttons, cards, menus)
- Creating micro-interactions and hover effects
- Implementing page transitions and route animations
- Adding scroll-based animations and parallax effects
- Animating layout changes (resizing, reordering, shared element transitions)
- Drag-and-drop interfaces
- Complex animation sequences and state-based animations
- Replacing CSS transitions with more powerful, controllable animations

**Technology:**
- **Motion** (v11+) - The modern, smaller library from Framer Motion creators
- **Framer Motion** - The full-featured predecessor (still widely used)
- React 18+ compatible, also supports Vue
- Supports TypeScript
- Works with Next.js, Vite, Remix, and all modern React frameworks

## Core Concepts

### 1. Motion Components

Convert any HTML/SVG element into an animatable component by prefixing with `motion.`:

```jsx
import { motion } from "motion/react"

// Regular HTML becomes motion component
<motion.div />
<motion.button />
<motion.svg />
<motion.path />
```

Every motion component accepts animation props like `animate`, `initial`, `transition`, and gesture props like `whileHover`, `whileTap`, etc.

### 2. Animate Prop

The `animate` prop defines the target animation state. When values change, Motion automatically animates to them:

```jsx
// Simple animation - x position changes
<motion.div animate={{ x: 100 }} />

// Multiple properties
<motion.div animate={{ x: 100, opacity: 1, scale: 1.2 }} />

// Animates when state changes
const [isOpen, setIsOpen] = useState(false)
<motion.div animate={{ width: isOpen ? 300 : 100 }} />
```

### 3. Initial State

Set the initial state before animation using the `initial` prop:

```jsx
<motion.div
  initial={{ opacity: 0, y: 50 }}
  animate={{ opacity: 1, y: 0 }}
/>
```

Set `initial={false}` to disable initial animations on mount.

### 4. Transitions

Control how animations move between states using the `transition` prop:

```jsx
// Duration-based
<motion.div
  animate={{ x: 100 }}
  transition={{ duration: 0.5, ease: "easeInOut" }}
/>

// Spring physics
<motion.div
  animate={{ scale: 1.2 }}
  transition={{ type: "spring", stiffness: 300, damping: 20 }}
/>

// Different transitions for different properties
<motion.div
  animate={{ x: 100, opacity: 1 }}
  transition={{
    x: { type: "spring", stiffness: 300 },
    opacity: { duration: 0.2 }
  }}
/>
```

**Transition types:**
- `"tween"` (default) - Duration-based with easing
- `"spring"` - Physics-based spring animation
- `"inertia"` - Decelerating animation (used in drag)

### 5. Variants

Organize animation states using named variants for cleaner code and propagation to children:

```jsx
const variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
  exit: { opacity: 0, scale: 0.9 }
}

<motion.div
  variants={variants}
  initial="hidden"
  animate="visible"
  exit="exit"
/>
```

**Variant propagation** - Children automatically inherit parent variant states:

```jsx
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1  // Stagger child animations
    }
  }
}

const itemVariants = {
  hidden: { x: -20, opacity: 0 },
  visible: { x: 0, opacity: 1 }
}

<motion.ul variants={containerVariants} initial="hidden" animate="visible">
  <motion.li variants={itemVariants} />
  <motion.li variants={itemVariants} />
</motion.ul>
```

## Common Patterns

### 1. Hover Animations

```jsx
<motion.button
  whileHover={{ scale: 1.1 }}
  transition={{ duration: 0.2 }}
>
  Hover me
</motion.button>
```

### 2. Tap/Press Animations

```jsx
<motion.button
  whileTap={{ scale: 0.95 }}
>
  Click me
</motion.button>
```

### 3. Exit Animations (AnimatePresence)

```jsx
import { AnimatePresence, motion } from "motion/react"

<AnimatePresence>
  {isVisible && (
    <motion.div
      key="modal"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    />
  )}
</AnimatePresence>
```

### 4. Staggered Animations

```jsx
const container = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
}

const item = {
  hidden: { x: -20, opacity: 0 },
  visible: { x: 0, opacity: 1 }
}

<motion.ul variants={container} initial="hidden" animate="visible">
  {items.map(i => <motion.li key={i} variants={item}>{i}</motion.li>)}
</motion.ul>
```

### 5. Spring Animations

```jsx
<motion.div
  animate={{ scale: 1.2 }}
  transition={{ type: "spring", stiffness: 300, damping: 20 }}
/>
```

## Performance Notes

- Use transform properties (x, y, scale, rotate) for hardware acceleration
- Use `layout="position"` for cheaper layout animations
- Use `useReducedMotion()` hook for accessibility
- Wrap exit-animated components in `<AnimatePresence>`
