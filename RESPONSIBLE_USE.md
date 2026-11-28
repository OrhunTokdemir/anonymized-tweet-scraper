<!-- guidelines-version: 2 -->
# Responsible use / Sorumlu kullanım

*This text is informational and is not legal advice. · Bu metin bilgilendirme amaçlıdır, hukuki tavsiye değildir.*

## English

This document is guidance only. It does not modify or add conditions to the MIT License, which alone governs use of this software.

anonymized-tweet-scraper ("the software") was designed for academic research. Collecting posts by real people carries legal and ethical responsibilities, and we strongly recommend the following.

1. **Follow the platforms' rules.** Check the terms of every platform you collect from.
   - X (Twitter)'s Terms of Service prohibit crawling or scraping without X's prior written consent, and prohibit getting around technical restrictions. Where possible, we recommend the official X API or, for research on systemic risks in the EU, the researcher data access route of the EU Digital Services Act (Art. 40).
   - Ekşi Sözlük is accessed through its unofficial mobile API. Please check Ekşi Sözlük's terms of use before collecting.
2. **Respect technical limits.** The software respects X's rate limits: an account that hits a limit is not used again until that limit resets. It is not designed to evade rate limits, blocks or account suspensions. Please do not modify it to do so, and use only accounts you are entitled to use.
3. **Data protection law.** Collected posts are personal data, so applicable law applies, including KVKK (Türkiye, Law No. 6698) and the GDPR (EU). The output is **pseudonymized, not anonymous**: the exact text and its timestamp can usually be traced back to the author. Posts can reveal special categories of data (e.g. religion, ethnicity, political opinion, sexual orientation, health), which are subject to stricter rules (KVKK Art. 6, GDPR Art. 9).
4. **Ethics approval.** Where your institution requires it, we recommend getting ethics committee approval **before** collecting data.
5. **No misuse.** Please do not use the software or its output for harassment, surveillance, profiling or targeting of individuals, spam, or any unlawful purpose, and please do not try to re-identify the people behind the posts.
6. **Responsible handling.** We recommend storing collected data securely, keeping only what your study needs, and deleting it when it is no longer needed. Please do not publish raw post text or verbatim quotes that identify people.
7. **Your data stays with you.** The software sends nothing to its author.

## Türkçe

Bu belge yalnızca yönlendirme amaçlıdır. Bu yazılımın kullanımını tek başına düzenleyen MIT Lisansı'nı değiştirmez ve ona herhangi bir koşul eklemez.

anonymized-tweet-scraper ("yazılım") akademik araştırma için tasarlanmıştır. Gerçek kişilerin gönderilerini toplamak hukuki ve etik sorumluluklar getirir; aşağıdakileri önemle tavsiye ederiz.

1. **Platform kurallarına uyun.** Veri topladığınız her platformun koşullarını kontrol edin.
   - X (Twitter) Hizmet Şartları, X'in önceden yazılı izni olmadan tarama (crawling) ve kazımayı (scraping) ve teknik kısıtlamaların aşılmasını yasaklar. Mümkünse resmî X API'sini veya AB'deki sistemik riskler üzerine araştırmalar için AB Dijital Hizmetler Yasası'nın (DSA, Md. 40) araştırmacı veri erişimi yolunu kullanmanızı öneririz.
   - Ekşi Sözlük'e resmî olmayan mobil API üzerinden erişilir. Veri toplamadan önce lütfen Ekşi Sözlük'ün kullanım koşullarını kontrol edin.
2. **Teknik sınırlara saygı gösterin.** Yazılım X'in hız sınırlarına uyar: sınıra takılan bir hesap, o sınır sıfırlanana kadar yeniden kullanılmaz. Yazılım hız sınırlarını, engellemeleri veya hesap askıya almalarını aşmak için tasarlanmamıştır. Lütfen yazılımı bu amaçla değiştirmeyin ve yalnızca kullanma hakkınız olan hesapları kullanın.
3. **Kişisel verilerin korunması.** Toplanan gönderiler kişisel veridir; bu nedenle KVKK (6698 sayılı Kanun) ve GDPR (AB) dahil yürürlükteki mevzuat uygulanır. Çıktı **takma adlandırılmıştır (pseudonymized), anonim değildir**: metnin aynısı ve zaman damgası çoğu zaman yazarına kadar izlenebilir. Gönderiler özel nitelikli kişisel verileri (ör. din, etnik köken, siyasi düşünce, cinsel yönelim, sağlık) ortaya koyabilir; bunlar daha sıkı kurallara tabidir (KVKK Md. 6, GDPR Md. 9).
4. **Etik kurul onayı.** Kurumunuz gerektiriyorsa, veri toplamaya **başlamadan önce** etik kurul onayı almanızı öneririz.
5. **Kötüye kullanmayın.** Lütfen yazılımı veya çıktısını taciz, gözetleme, kişilerin profillenmesi veya hedef alınması, spam ya da hukuka aykırı herhangi bir amaçla kullanmayın ve gönderilerin arkasındaki kişileri yeniden tanımlamaya çalışmayın.
6. **Sorumlu saklama.** Toplanan verileri güvenli saklamanızı, yalnızca çalışmanız için gerekeni tutmanızı ve gerekmediğinde silmenizi öneririz. Lütfen kişileri tanımlayabilecek ham gönderi metinlerini veya birebir alıntıları yayımlamayın.
7. **Verileriniz sizde kalır.** Yazılım yazarına hiçbir veri göndermez.
