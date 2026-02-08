import React from 'react'

const STORAGE_KEY = 'theme' // "dark" | "light"

function applyTheme(theme) {
  const root = document.documentElement // <html>
  if (theme === 'dark') root.classList.add('dark')
  else root.classList.remove('dark')
}

function getInitialTheme() {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved === 'dark' || saved === 'light') return saved

  const prefersDark = window.matchMedia?.(
    '(prefers-color-scheme: dark)'
  )?.matches
  return prefersDark ? 'dark' : 'light'
}

export default function DarkModeToggle() {
  const [theme, setTheme] = React.useState(() => getInitialTheme())

  // mount + theme 변경 시 적용/저장
  React.useEffect(() => {
    applyTheme(theme)
    localStorage.setItem(STORAGE_KEY, theme)
  }, [theme])

  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm text-accent hover:bg-muted"
      aria-pressed={isDark}
      aria-label="Toggle dark mode"
    >
      {isDark ? (
        // 다크모드일 때: 태양 아이콘 표시 (라이트모드로 전환용)
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="lucide lucide-sun animate-in zoom-in-50 duration-300"
        >
          <circle cx="12" cy="12" r="4"></circle>
          <path d="M12 2v2"></path>
          <path d="M12 20v2"></path>
          <path d="m4.93 4.93 1.41 1.41"></path>
          <path d="m17.66 17.66 1.41 1.41"></path>
          <path d="M2 12h2"></path>
          <path d="M20 12h2"></path>
          <path d="m6.34 17.66-1.41 1.41"></path>
          <path d="m19.07 4.93-1.41 1.41"></path>
        </svg>
      ) : (
        // 라이트모드일 때: 달 아이콘 표시 (다크모드로 전환용)
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="lucide lucide-moon animate-in zoom-in-50 duration-300"
        >
          <path d="M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401"></path>
        </svg>
      )}
    </button>
  )
}
