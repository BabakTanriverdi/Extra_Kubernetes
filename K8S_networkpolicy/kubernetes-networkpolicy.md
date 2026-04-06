# Kubernetes NetworkPolicy — Kapsamlı Hands-on Rehberi

> **Amaç:** Bu belge, Kubernetes ortamında pod-pod ve namespace arası ağ trafiğini kontrol etmek için kullanılan `NetworkPolicy` nesnesini **sıfırdan**, hiçbir soru kalmayacak şekilde anlatır. Her adımın **neden** yapıldığı, **ne anlama geldiği** ve **ne sağladığı** detaylı biçimde açıklanmıştır.

---

## İçindekiler

1. [Ön Bilgi: Kubernetes Ağ Modeli](#ön-bilgi-kubernetes-ağ-modeli)
2. [NetworkPolicy Nedir? Neden Gereklidir?](#networkpolicy-nedir-neden-gereklidir)
3. [Part 1 — Kubernetes Cluster Kurulumu](#part-1--kubernetes-cluster-kurulumu)
4. [Part 2 — Ortamın Hazırlanması](#part-2--ortamın-hazırlanması)
5. [Part 3 — NetworkPolicy Nesnesi](#part-3--networkpolicy-nesnesi)
   - [3.1 Temel NetworkPolicy (Namespace bazlı)](#31-temel-networkpolicy-namespace-bazlı)
   - [3.2 Gelişmiş NetworkPolicy (ipBlock + OR mantığı)](#32-gelişmiş-networkpolicy-ipblock--or-mantığı)
   - [3.3 AND Mantığı (namespaceSelector + podSelector birlikte)](#33-and-mantığı-namespaceselector--podselector-birlikte)
6. [Sık Yapılan Hatalar ve İpuçları](#sık-yapılan-hatalar-ve-ipuçları)

---

## Ön Bilgi: Kubernetes Ağ Modeli

Kubernetes'te her pod, cluster içinde **benzersiz bir IP adresi** alır. Varsayılan olarak:

- Her pod, diğer **tüm** podlarla konuşabilir (NAT olmadan, düz IP ile).
- Namespace engeli yoktur; farklı namespace'teki podlar birbirini doğrudan arayabilir.
- Bu model büyük kolaylık sağlar ama aynı zamanda **güvenlik açığı** oluşturur.

> **Senaryo:** Bir e-ticaret uygulamanızda `frontend`, `backend` ve `veritabanı` podları var. Varsayılan durumda `frontend` pod'u, `veritabanı` pod'una **doğrudan** erişebilir. Bu son derece tehlikeli bir durumdur.

**NetworkPolicy**, bu varsayılan "herkese açık" modeli değiştirip trafiği kısıtlamamızı sağlar.

---

## NetworkPolicy Nedir? Neden Gereklidir?

**NetworkPolicy**, Kubernetes'in yerel bir API nesnesidir. OSI modelinin **3. katmanı (IP)** ve **4. katmanı (Port/Protokol)** seviyesinde trafik kontrolü sağlar.

### Ne Sağlar?

| Özellik | Açıklama |
|---|---|
| **Ingress (Gelen Trafik)** | Pod'a hangi kaynaklardan trafik gelebileceğini tanımlar |
| **Egress (Giden Trafik)** | Pod'un hangi hedeflere trafik gönderebileceğini tanımlar |
| **Pod Seçimi** | `podSelector` ile hangi pod(lar)a uygulanacağını belirler |
| **IP Bloğu** | CIDR notasyonuyla belirli IP aralıklarına izin veya yasak |
| **Namespace Kısıtı** | Hangi namespace'lerden gelen trafiğin geçeceğini belirler |

### Önemli Kural

> NetworkPolicy, **varsayılan olarak izin verir** (whitelist değil, blacklist gibi davranır). Ancak bir pod'a **herhangi bir** NetworkPolicy uygulandığı anda, o NetworkPolicy'de **belirtilmeyen tüm trafik engellenir**. Yani "izin verilenler dışında her şey yasaklanır" (whitelist) moduna geçilir.

### CNI Eklentisi Gereksinimi

NetworkPolicy kuralları, Kubernetes API'si tarafından sadece **depolanır**; ancak **uygulanması** CNI (Container Network Interface) eklentisine bağlıdır. Varsayılan Kubernetes kurulumunda gelen `kubenet` NetworkPolicy'yi **desteklemez**.

NetworkPolicy'yi destekleyen popüler CNI'lar:
- **Calico** ✅ (Bu hands-on'da kullanılır)
- Cilium ✅
- Weave Net ✅
- Flannel ❌ (NetworkPolicy desteklemez)

---

## Part 1 — Kubernetes Cluster Kurulumu

### Amaç
Bu bölümde iki node'lu (1 master, 1 worker) bir Kubernetes cluster'ı ayağa kaldırıyoruz. Gerçek dünya senaryolarını simüle etmek için birden fazla namespace kullanacağız.

### Cluster'ı Terraform ile Oluşturma

```bash
# Terraform ile cluster oluşturun
# master node hazır olduğunda worker otomatik olarak cluster'a katılır
terraform init
terraform apply
```

> **Not:** Yerel ortamda denemek isteyenler için alternatif: [https://labs.play-with-k8s.com](https://labs.play-with-k8s.com) — ücretsiz, tarayıcı tabanlı Kubernetes playground.

### Cluster'ın Sağlıklı Çalıştığını Doğrulama

```bash
# Cluster'ın kontrol düzlemi (API server, etcd, scheduler vb.) hazır mı?
kubectl cluster-info

# Node'ların "Ready" durumunda olup olmadığını kontrol et
kubectl get nodes
```

**Beklenen Çıktı:**
```
NAME          STATUS   ROLES           AGE   VERSION
master-node   Ready    control-plane   5m    v1.32.x
worker-node   Ready    <none>          4m    v1.32.x
```

---

## Part 2 — Ortamın Hazırlanması

### Senaryo

Bu hands-on'da üç uygulama simüle ediyoruz:

| Uygulama | Namespace | Açıklama |
|---|---|---|
| `myshop` | `myshop-ns` | E-ticaret frontend uygulaması |
| `mydb` | `mydb-ns` | Veritabanı servisi |
| `nginx` | `nginx-ns` | Başka bir uygulama (db'ye erişmemesi gereken) |

**Hedef:** `myshop` → `mydb`'ye erişebilsin, `nginx` → `mydb`'ye **erişemesin**.

---

### Adım 1 — Calico CNI Kurulumu

#### Neden Calico?
Standart Kubernetes kurulumu NetworkPolicy kurallarını **uygulamaz**, sadece API'ye kaydeder. Calico, bu kuralları gerçek anlamda işleten ağ bileşenidir. Calico olmadan yazdığınız tüm NetworkPolicy'ler işlevsiz olur.

```bash
# Helm binary'yi indir ve kur
# get-helm-3 scripti her zaman en güncel kararlı sürümü indirir
# Nisan 2026 itibarıyla güncel sürüm: Helm v4.1.3
curl https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash

# Helm sürümünü doğrula
helm version
```

**Beklenen Çıktı:**
```
version.BuildInfo{Version:"v4.1.3", GitCommit:"...", GitTreeState:"clean", GoVersion:"go1.24.x"}
```

> **Not:** Helm 4, Kasım 2025'te yayınlanan ilk major sürümdür. Helm 3 desteği Temmuz 2026'ya kadar devam edecek, ancak yeni kurulumlar için Helm 4 önerilir.

```bash
# Tigera (Calico'nun sahibi şirket) Helm repository'sini ekle
helm repo add projectcalico https://docs.tigera.io/calico/charts

# Repository index'ini güncelle (yeni chart versiyonlarını çek)
helm repo update

# tigera-operator namespace'ini oluştur
# Calico'nun yönetici bileşeni (Operator) bu namespace'te çalışır
kubectl create namespace tigera-operator

# Calico'yu kur — v3.31.4 güncel kararlı sürüm (Nisan 2026 itibarıyla)
# --namespace: Operatörün hangi namespace'e kurulacağı
helm install calico projectcalico/tigera-operator \
  --version v3.31.4 \
  --namespace tigera-operator

# Calico sistem pod'larının ayağa kalkmasını izle
# Tüm pod'lar "Running" olana kadar bekle
watch kubectl get pods -n calico-system
```

**Beklenen Çıktı (tüm pod'lar Running olduğunda):**
```
NAME                                       READY   STATUS    RESTARTS   AGE
calico-kube-controllers-xxxxxxxxxx-xxxxx   1/1     Running   0          2m
calico-node-xxxxx                          1/1     Running   0          2m
calico-typha-xxxxxxxxxx-xxxxx              1/1     Running   0          2m
```

> **`watch` komutu:** Terminal'de komutu her 2 saniyede yeniler. Çıkmak için `Ctrl+C`.

---

### Adım 2 — Namespace'lerin Oluşturulması

#### Neden Ayrı Namespace?
Namespace'ler, Kubernetes'te mantıksal izolasyon birimidir. NetworkPolicy'de namespace etiketlerine göre trafik yönlendirmesi yapabilirsiniz. Gerçek dünyada farklı ekipler veya uygulamalar farklı namespace'lerde çalışır.

```bash
# Üç uygulama için ayrı namespace oluştur
kubectl create ns myshop-ns   # E-ticaret uygulaması namespace'i
kubectl create ns mydb-ns     # Veritabanı namespace'i
kubectl create ns nginx-ns        # Nginx namespace'i
```

---

### Adım 3 — Proje Klasörü Oluşturma

```bash
# Tüm YAML dosyalarını tek bir klasörde topla
mkdir np-project && cd np-project
```

---

### Adım 4 — Deployment ve Service YAML Dosyalarının Oluşturulması

#### myshop.yaml

```yaml
# ─────────────────────────────────────────────────────────────────────────────
# Deployment: myshop uygulamasını çalıştırır
# ─────────────────────────────────────────────────────────────────────────────
apiVersion: apps/v1          # Deployment API sürümü
kind: Deployment             # Nesne tipi
metadata:
  name: myshop-deployment
  namespace: myshop-ns   # Bu deployment myshop-ns içinde çalışır
spec:
  replicas: 1                # Kaç pod çalıştırılacak
  selector:
    matchLabels:
      app: myshop        # Bu selector, aşağıdaki template.metadata.labels ile eşleşmeli
  template:
    metadata:
      labels:
        app: myshop      # Pod etiketi — NetworkPolicy bu etiketi kullanarak pod'u seçer
    spec:
      containers:
      - name: myshop
        image: babaktanriverdi/myshop:v1   # Docker Hub'dan çekilen uygulama imajı
        ports:
        - containerPort: 80  # Container içinde dinlenen port

---
# ─────────────────────────────────────────────────────────────────────────────
# Service: myshop deployment'ına cluster içi sabit DNS adı verir
# ─────────────────────────────────────────────────────────────────────────────
apiVersion: v1
kind: Service
metadata:
  name: myshop-svc
  namespace: myshop-ns   # Service ile Deployment aynı namespace'te olmalı
spec:
  type: ClusterIP             # Sadece cluster içinden erişilebilir (dışarıya açılmaz)
  ports:
  - port: 80                  # Service'in dinleyeceği port
    targetPort: 80            # Pod üzerindeki hedef port (containerPort ile aynı olmalı)
  selector:
    app: myshop           # Bu etiketle eşleşen pod'lara trafik yönlendirilir
```

#### nginx.yaml

```yaml
# ─────────────────────────────────────────────────────────────────────────────
# Deployment: Nginx — mydb'ye erişmemesi gereken "yabancı" uygulama
# ─────────────────────────────────────────────────────────────────────────────
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  namespace: nginx-ns        # nginx-ns namespace'inde çalışır
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx            # Pod etiketi
    spec:
      containers:
      - name: nginx
        image: nginx          # Standart nginx imajı (Docker Hub'dan)
        ports:
        - containerPort: 80

---
apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
  namespace: nginx-ns
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: nginx
```

#### mydb.yaml

```yaml
# ─────────────────────────────────────────────────────────────────────────────
# Deployment: mydb — korunması gereken veritabanı uygulaması
# ─────────────────────────────────────────────────────────────────────────────
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mydb-deployment
  namespace: mydb-ns     # Veritabanı kendi namespace'inde izole çalışır
spec:
  replicas: 1
  selector:
    matchLabels:
      db: mydb            # NOT: Burada "db" key kullanıldı, "app" değil
  template:
    metadata:
      labels:
        db: mydb          # Pod etiketi — NetworkPolicy'de podSelector bu etiketi kullanır
    spec:
      containers:
      - name: mydb
        image: babaktanriverdi/mydb:v1
        ports:
        - containerPort: 80

---
apiVersion: v1
kind: Service
metadata:
  name: mydb-svc
  namespace: mydb-ns
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 80
  selector:
    db: mydb              # "db: mydb" etiketli pod'lara yönlendir
```

---

### Adım 5 — Tüm Kaynakları Uygulama

```bash
# np-project klasöründeki TÜM .yaml dosyalarını tek seferde uygula
# kubectl apply -f . → mevcut dizindeki tüm YAML'ları sırayla uygular
kubectl apply -f .
```

---

### Adım 6 — NetworkPolicy Öncesi Test (Her Yer Erişilebilir)

Bu test, NetworkPolicy uygulamadan önce trafik durumunu belgeler. **Her pod her pod'a erişebilmeli** — bu varsayılan Kubernetes davranışıdır.

```bash
# Tüm pod ve service'leri listele (IP adreslerini not et)
kubectl get pods,svc -A -o wide
```

```bash
# myshop pod'u içine gir (pod adını yukarıdaki çıktıdan al)
kubectl -n myshop-ns exec -it \
  $(kubectl get pod -n myshop-ns -l app=myshop -o jsonpath='{.items[0].metadata.name}') \
  -- sh

# mydb pod'una IP ile bağlan (IP'yi kubectl get pods çıktısından al)
apk add curl
curl <mydb-pod-ip>

# DNS ile bağlan: <service-adı>.<namespace> formatı cluster içinde çözümlenir
curl mydb-svc.mydb-ns

exit
```

```bash
# nginx pod'u içine gir
kubectl -n nginx-ns exec -it \
  $(kubectl get pod -n nginx-ns -l app=nginx -o jsonpath='{.items[0].metadata.name}') \
  -- bash

# nginx'ten de mydb'ye erişilebilmeli (henüz policy yok)
curl <mydb-pod-ip>
curl mydb-svc.mydb-ns

exit
```

> **Beklenen Sonuç:** Her iki pod da mydb'ye başarıyla bağlanır. Bu **güvenli değildir** — NetworkPolicy ile düzelteceğiz.

---

## Part 3 — NetworkPolicy Nesnesi

### 3.1 Temel NetworkPolicy (Namespace Bazlı)

#### Önce Namespace Etiketlerini Kontrol Et

```bash
# Kubernetes, her namespace'e otomatik olarak kendi adını etiket olarak ekler
# Bu etiketler NetworkPolicy'de namespaceSelector olarak kullanılır
kubectl get ns --show-labels
```

**Çıktı:**
```
NAME              STATUS   AGE   LABELS
mydb-ns       Active   10m   kubernetes.io/metadata.name=mydb-ns
myshop-ns     Active   10m   kubernetes.io/metadata.name=myshop-ns
nginx-ns          Active   10m   kubernetes.io/metadata.name=nginx-ns
default           Active   20m   kubernetes.io/metadata.name=default
kube-system       Active   20m   kubernetes.io/metadata.name=kube-system
```

> `kubernetes.io/metadata.name` etiketi Kubernetes 1.21+ sürümünde **otomatik** olarak eklenir. Bu sayede her namespace kendi adıyla etiketlenmiş olur ve NetworkPolicy'de kullanılabilir.

---

#### network-policy.yaml (Temel Sürüm)

```yaml
# ─────────────────────────────────────────────────────────────────────────────
# NetworkPolicy: mydb pod'una trafik kontrolü
# AMAÇ: Sadece myshop-ns namespace'inden gelen trafik mydb'ye ulaşsın
# ─────────────────────────────────────────────────────────────────────────────
apiVersion: networking.k8s.io/v1   # NetworkPolicy API'si bu grup altında
kind: NetworkPolicy
metadata:
  name: test-network-policy
  namespace: mydb-ns           # Bu policy mydb-ns namespace'inde geçerli

spec:

  podSelector:                     # Bu policy hangi pod'lara uygulanacak?
    matchLabels:
      db: mydb                 # "db: mydb" etiketli pod'ları seç (mydb pod'ları)
                                   # NOT: Boş bırakılırsa namespace'teki TÜM pod'lar seçilir

  policyTypes:                     # Hangi trafik yönleri kontrol edilecek?
    - Ingress                      # Gelen trafiği kısıtla
    - Egress                       # Giden trafiği kısıtla
                                   # Her ikisi de belirtildiği için hem gelen hem giden
                                   # bu policy'de tanımlananlar dışında engellenir

  ingress:                         # Gelen trafik kuralları
    - from:                        # Kimlerden gelen trafik izinli?
        - namespaceSelector:       # Namespace bazlı seçim
            matchLabels:
              kubernetes.io/metadata.name: myshop-ns
              # Yalnızca "myshop-ns" etiketine sahip namespace'ten gelen trafik izinli
              # nginx-ns, default, kube-system vb. engellenecek
      ports:                       # Hangi portlara gelen trafik izinli?
        - protocol: TCP
          port: 80                 # Sadece TCP/80'e izin ver

  egress:                          # Giden trafik kuralları
    - to:                          # Nereye gidecek trafiğe izin var?
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: myshop-ns
              # mydb, sadece myshop-ns'e trafik gönderebilir
              # İnternete, diğer namespace'lere çıkış engellenecek
      ports:
        - protocol: TCP
          port: 80
```

**Bu policy şunu sağlar:**
- `mydb` pod'u artık bir **"kale"** gibidir.
- İçeri girebilecek tek ziyaretçi: `myshop-ns` namespace'indeki pod'lar.
- Dışarı çıkış da sadece `myshop-ns`'e yapılabilir.
- `nginx-ns`'ten gelen her bağlantı girişimi **düşer (drop)**.

```bash
# Policy'yi uygula
kubectl apply -f network-policy.yaml

# Policy'nin oluşturulduğunu doğrula
kubectl get networkpolicy -n mydb-ns

# Detaylı görüntüle
kubectl describe networkpolicy test-network-policy -n mydb-ns
```

#### Test

```bash
# myshop → mydb: BAŞARILI olmalı ✅
kubectl -n myshop-ns exec -it \
  $(kubectl get pod -n myshop-ns -l app=myshop -o jsonpath='{.items[0].metadata.name}') \
  -- sh
curl mydb-svc.mydb-ns     # Bağlantı başarılı olmalı
exit

# nginx → mydb: BAŞARISIZ olmalı ❌
kubectl -n nginx-ns exec -it \
  $(kubectl get pod -n nginx-ns -l app=nginx -o jsonpath='{.items[0].metadata.name}') \
  -- bash
curl --max-time 5 mydb-svc.mydb-ns   # Timeout / bağlantı reddedilmeli
exit
```

---

### 3.2 Gelişmiş NetworkPolicy (ipBlock + OR Mantığı)

Bu sürümde **üç farklı kaynak türünü** bir araya getiriyoruz:
1. IP bloğu (CIDR)
2. Namespace seçici
3. Pod seçici

Bu üç seçici arasındaki mantık **OR (VEYA)**'dır — herhangi biri karşılanırsa bağlantıya izin verilir.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: test-network-policy
  namespace: mydb-ns
spec:
  podSelector:
    matchLabels:
      db: mydb

  policyTypes:
    - Ingress
    - Egress

  ingress:
    - from:
        # ── Kaynak 1: IP Bloğu (CIDR) ──────────────────────────────────────
        - ipBlock:
            cidr: 172.16.0.0/16        # 172.16.x.x aralığındaki TÜM IP'ler.
            except:
              - 172.16.180.0/24        # Bu alt ağ (172.16.180.0–172.16.180.255) hariç
                                       # CIDR + except = ince ayarlı IP kontrolü
                                       # Örnek: Belirli bir ofis bloğunu veya DMZ'yi hariç tutmak

        # ── Kaynak 2: Namespace Seçici ─────────────────────────────────────
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: myshop-ns
              # myshop-ns namespace'indeki tüm pod'lardan gelen trafik

        # ── Kaynak 3: Pod Seçici ────────────────────────────────────────────
        - podSelector:
            matchLabels:
              role: frontend
              # mydb-ns namespace'inde "role: frontend" etiketine sahip pod'lar
              # NOT: podSelector tek başına kullanıldığında AYNI namespace'teki pod'ları seçer

      ports:
        - protocol: TCP
          port: 80

  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: myshop-ns
      ports:
        - protocol: TCP
          port: 80
```

#### OR Mantığı Görsel Açıklaması

```
mydb'ye erişim izni:
┌────────────────────────────────────────────────────────┐
│  KAYNAK 1: IP 172.16.0.0/16 (172.16.180.0/24 hariç)    │
│  VEYA                                                  │
│  KAYNAK 2: myshop-ns namespace'indeki herhangi pod     │
│  VEYA                                                  │
│  KAYNAK 3: mydb-ns içinde role=frontend olan pod       │
└────────────────────────────────────────────────────────┘
  → Yukarıdakilerden HERHANGİ BİRİ doğruysa → ERİŞİM İZİNLİ
```

> **Dikkat:** `from` altındaki her `-` (tire) ayrı bir kaynaktır ve aralarındaki ilişki **OR**'dur. Bunu aşağıdaki AND mantığıyla karıştırmayın.

```bash
kubectl apply -f network-policy.yaml
```

Test ettiğinizde nginx pod'u `myshop-ns`'te olmadığı için engellenmeye devam eder. Ancak 172.16.0.0/16 IP bloğundan veya `role: frontend` etiketli pod'lardan erişim açılmıştır.

---

### 3.3 AND Mantığı (namespaceSelector + podSelector birlikte)

Bu sürüm en **kısıtlayıcı** olanıdır. Erişim için **iki koşulun aynı anda** sağlanması gerekir:
1. Pod, `myshop-ns` namespace'inde olmalı **VE**
2. Pod, `role: frontend` etiketine sahip olmalı

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: test-network-policy
  namespace: mydb-ns
spec:
  podSelector:
    matchLabels:
      db: mydb

  policyTypes:
    - Ingress
    - Egress

  ingress:
    - from:
        # ─────────────────────────────────────────────────────────────────────
        # AND MANTIĞI: namespaceSelector ve podSelector AYNI liste elemanında
        # (aynı "-" altında, "- " olmadan bitişik yazılır)
        #
        # Bu kural: "myshop-ns namespace'inde VE role=frontend etiketli pod"
        # Her iki koşul aynı anda sağlanmalı.
        #
        # KARŞILAŞTIRMA:
        # OR (ayrı bloklar — önceki örnekte gösterildi):
        #   - namespaceSelector: ...    ← ayrı tire
        #   - podSelector: ...          ← ayrı tire
        #
        # AND (aynı blok — bu örnek):
        #   - namespaceSelector: ...    ← tek tire
        #     podSelector: ...          ← tire yok, üstle aynı öğe
        # ─────────────────────────────────────────────────────────────────────
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: myshop-ns
          podSelector:               # Dikkat: Bu "-" değil, üstteki ile aynı seviye
            matchLabels:
              role: frontend         # myshop-ns'te VE role=frontend olan pod

      ports:
        - protocol: TCP
          port: 80

  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: myshop-ns
      ports:
        - protocol: TCP
          port: 80
```

#### YAML Girintisi Kritik Öneme Sahip

```yaml
# ✅ DOĞRU — AND mantığı (her iki koşul aynı anda gerekli)
- from:
  - namespaceSelector:          # tek tire
      matchLabels:
        kubernetes.io/metadata.name: myshop-ns
    podSelector:                # tire YOK — üsttekiyle aynı öğe
      matchLabels:
        role: frontend

# ❌ YANLIŞ olurdu — OR mantığı (iki ayrı kaynak, birinin sağlanması yeter)
- from:
  - namespaceSelector:          # birinci tire
      matchLabels:
        kubernetes.io/metadata.name: myshop-ns
  - podSelector:                # ikinci tire — AYRI öğe
      matchLabels:
        role: frontend
```

```bash
kubectl apply -f network-policy.yaml
```

#### Test — İlk Deneme (Başarısız Olacak)

```bash
# myshop pod'u role=frontend etiketine henüz sahip değil → erişim engellenir
kubectl -n myshop-ns exec -it \
  $(kubectl get pod -n myshop-ns -l app=myshop -o jsonpath='{.items[0].metadata.name}') \
  -- sh
curl --max-time 5 mydb-svc.mydb-ns   # Timeout — beklenen
exit
```

#### myshop.yaml'a Etiket Ekleme

`myshop` pod'unun `role: frontend` etiketini alması için `myshop.yaml` dosyasını güncelleyin:

```yaml
# myshop.yaml — Güncellenmiş sürüm
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myshop-deployment
  namespace: myshop-ns
spec:
  replicas: 1
  selector:
    matchLabels:
      app: myshop
  template:
    metadata:
      labels:
        app: myshop
        role: frontend           # ← YENİ EKLENEN ETİKET
                                 # NetworkPolicy'nin AND koşulunu karşılar
    spec:
      containers:
      - name: myshop
        image: babaktanriverdi/myshop
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: myshop-svc
  namespace: myshop-ns
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: myshop
```

```bash
# Güncellenmiş deployment'ı uygula
# kubectl apply -f: Mevcut kaynakları günceller, yoksa oluşturur (idempotent)
kubectl apply -f myshop.yaml

# Yeni pod'un ayağa kalkmasını bekle
kubectl rollout status deployment/myshop-deployment -n myshop-ns
```

#### Test — İkinci Deneme (Başarılı Olacak)

```bash
# Artık myshop pod'u hem myshop-ns'te hem de role=frontend etiketine sahip
# AND koşulunun iki şartı da karşılandı → erişim izinli ✅
kubectl -n myshop-ns exec -it \
  $(kubectl get pod -n myshop-ns -l app=myshop -o jsonpath='{.items[0].metadata.name}') \
  -- sh
curl mydb-svc.mydb-ns    # Başarılı!
exit

# nginx hâlâ erişemiyor ❌
kubectl -n nginx-ns exec -it \
  $(kubectl get pod -n nginx-ns -l app=nginx -o jsonpath='{.items[0].metadata.name}') \
  -- bash
curl --max-time 5 mydb-svc.mydb-ns   # Timeout — beklenen
exit
```

---

## Sık Yapılan Hatalar ve İpuçları

### 1. CNI Eklentisi Olmadan NetworkPolicy Çalışmaz

```bash
# Calico'nun çalışıp çalışmadığını kontrol et
kubectl get pods -n calico-system
# Tüm pod'lar "Running" olmalı
```

### 2. NetworkPolicy Sadece TCP/UDP/SCTP'ye Uygulanır

ICMP (ping) varsayılan olarak NetworkPolicy kapsam dışındadır. `curl` kullanın, `ping` değil.

### 3. Policy Silme = Trafik Tekrar Açılır

```bash
# Policy'yi sil → mydb tekrar herkese açılır
kubectl delete networkpolicy test-network-policy -n mydb-ns
```

### 4. Tüm Policy'leri Listeleme

```bash
# Belirli bir namespace'teki tüm policy'leri listele
kubectl get networkpolicy -n mydb-ns

# Tüm namespace'lerde tüm policy'leri listele
kubectl get networkpolicy -A
```

### 5. Policy Detayını İnceleme

```bash
kubectl describe networkpolicy test-network-policy -n mydb-ns
```

### 6. Hızlı Referans: OR vs AND

| Senaryo | YAML Yapısı | Örnek Kullanım |
|---|---|---|
| **OR** | `from` altında birden fazla `-` (tire) | "Bu IP'den **veya** bu namespace'den gel" |
| **AND** | Aynı `-` altında iki seçici bitişik | "Bu namespace'den **ve** bu etikete sahip ol" |

---

## Özet: NetworkPolicy Karar Akışı

```
Pod'a trafik geldi
        │
        ▼
Bu pod'a uygulanmış herhangi bir NetworkPolicy var mı?
        │
   ┌────┴────┐
  YOK      VAR
   │         │
   ▼         ▼
İzinli    Gelen trafik NetworkPolicy'deki
(default)  ingress kurallarından herhangi birine uyuyor mu?
                │
           ┌────┴────┐
          EVET      HAYIR
           │         │
           ▼         ▼
        İzinli     Engelle (DROP)
```

---

> **Son Not:** NetworkPolicy, Kubernetes güvenliğinin ilk savunma hattıdır. Gerçek üretim ortamlarında her namespace için "varsayılan reddet" (default-deny) policy'si oluşturup üzerine izinleri eklemek en iyi pratiktir.
>
> ```yaml
> # Tüm namespace'i kilitleyen default-deny örneği
> apiVersion: networking.k8s.io/v1
> kind: NetworkPolicy
> metadata:
>   name: default-deny-all
>   namespace: mydb-ns
> spec:
>   podSelector: {}        # Boş = namespace'teki TÜM pod'lar
>   policyTypes:
>     - Ingress
>     - Egress
>   # Hiç ingress/egress kuralı yok = her şey engellendi
> ```
