import { BookOpen, ChevronDown } from 'lucide-react'

const PARAGRAPHS = [
  'Sistem önce videodaki yolu bir referans düzlemi olarak kalibre eder: operatör, görüntüde ' +
    'gerçek dünya mesafesi bilinen noktaları (şerit genişliği ~3,5 m, plaka 520×110 mm gibi) ' +
    'işaretler. Bu eşleşmelerden, görüntüdeki pikseller ile yoldaki gerçek metreler arasında ' +
    'matematiksel bir dönüşüm (homografi) kurulur; böylece ekrandaki her noktanın yolda kaç ' +
    'metreye karşılık geldiği bilinir.',
  'Araç, kareler boyunca otomatik takip edilir; ölçüm için aracın tekerlek–zemin temas noktası ' +
    'kullanılır (kütle merkezi değil — kamera açısı nedeniyle hata üretir). Bu nokta her karede ' +
    'gerçek dünya koordinatına çevrilir; iki kare arasında kat edilen metre, videonun kare hızı ' +
    '(FPS) ile birleştirilerek hıza çevrilir ve km/h cinsinden verilir.',
  'Hiçbir hız çıplak tek sayı olarak sunulmaz: her sonuç bir güven aralığı (örn. 52 ± 3 km/h) ve ' +
    'güven seviyesi taşır. Kalibrasyon kalitesi (hata payı) ölçülür ve operatör onayından geçer; ' +
    'tüm adımlar ile dosya bütünlüğü (SHA-256) loglanır, böylece sonuç bağımsız olarak ' +
    'doğrulanabilir.',
]

/** Bilirkişi için "Hız nasıl hesaplanıyor?" açılır bilgi kartı. */
export function MethodInfoCard() {
  return (
    <details className="group rounded-xl border bg-muted/30 shadow-card">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-medium [&::-webkit-details-marker]:hidden">
        <BookOpen className="size-4 text-primary" />
        Yöntem — Hız nasıl hesaplanıyor?
        <ChevronDown className="ml-auto size-4 text-muted-foreground transition-transform group-open:rotate-180" />
      </summary>
      <div className="space-y-2.5 border-t px-4 py-3 text-sm leading-relaxed text-muted-foreground">
        {PARAGRAPHS.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>
    </details>
  )
}
