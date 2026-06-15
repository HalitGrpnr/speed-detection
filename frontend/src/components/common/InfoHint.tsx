import { Info } from 'lucide-react'

/**
 * Sade açıklama balonu — bilirkişi için teknik terimlerin Türkçe karşılığı.
 * Native `title` yerine stillenmiş, hover'da anında açılan kutu.
 */
export function InfoHint({ text }: { text: string }) {
  return (
    <span className="group relative inline-flex align-middle">
      <Info className="size-3.5 cursor-help text-muted-foreground/50 transition-colors group-hover:text-primary" />
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-60 max-w-[16rem] -translate-x-1/2 rounded-lg border bg-popover px-3 py-2 text-xs font-normal leading-relaxed text-popover-foreground opacity-0 shadow-pop transition-opacity duration-150 group-hover:opacity-100"
      >
        {text}
      </span>
    </span>
  )
}
