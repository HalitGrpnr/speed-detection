function App() {
  return (
    <div className="min-h-screen bg-slate-100 text-slate-800">
      <header className="flex items-center gap-3 bg-slate-800 px-6 py-3 text-slate-100 shadow">
        <h1 className="text-lg font-semibold tracking-wide">Araç Hız Tespit Sistemi</h1>
        <span className="rounded-full bg-slate-900 px-2 py-0.5 text-xs text-slate-400">
          Yerel — Adli
        </span>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-16">
        <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">Frontend iskelesi hazır</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">
            M8 Step 0 tamamlandı — React + Vite + TypeScript + Tailwind kuruldu ve build
            çıktısı FastAPI tarafından servis ediliyor. Tasarım sistemi ve uygulama kabuğu
            (header, stepper, wizard) Step 1'de gelecek.
          </p>
        </div>
      </main>
    </div>
  )
}

export default App
