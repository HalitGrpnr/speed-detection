const APP_VERSION = 'v1.0'

/** Sade alt şerit: ürün adı + sürüm. */
export function Footer() {
  return (
    <footer className="flex h-9 shrink-0 items-center border-t bg-card/70 px-5 text-[11px] text-muted-foreground backdrop-blur-sm">
      <span className="font-medium text-foreground/70">
        Araç Hız Tespit Sistemi <span className="text-muted-foreground">· {APP_VERSION}</span>
      </span>
      <span className="ml-auto text-muted-foreground">Yerel masaüstü uygulaması</span>
    </footer>
  )
}
