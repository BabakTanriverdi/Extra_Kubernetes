# Kubernetes Hands-on: ServiceAccount ve RBAC Yetkilendirmesi

> **Amaç:** Bu uygulamalı eğitim, Kubernetes'teki `ServiceAccount` nesnelerini ve RBAC (Role-Based Access Control) yetkilendirme mekanizmasını kavramsal ve pratik düzeyde öğretmeyi hedefler.

---

## Öğrenme Hedefleri

Bu eğitimin sonunda öğrenciler:

- RBAC yetkilendirme modelini açıklayabilecek
- `ServiceAccount` nesnelerini oluşturup yönetebilecek
- `Role`, `ClusterRole`, `RoleBinding` ve `ClusterRoleBinding` nesnelerini kullanabilecek
- Pod'lara özel izinler tanımlayıp uygulayabilecek

---

## İçerik

- [Bölüm 1 – Kubernetes Cluster Kurulumu](#bölüm-1--kubernetes-cluster-kurulumu)
- [Bölüm 2 – ServiceAccount](#bölüm-2--serviceaccount)
- [Bölüm 3 – RBAC Yetkilendirmesi](#bölüm-3--rbac-yetkilendirmesi)

---

## Bölüm 1 – Kubernetes Cluster Kurulumu

### Cluster Hazırlama

Ubuntu 22.04 üzerinde iki node'lu (1 master, 1 worker) bir Kubernetes cluster'ı hazırlayın. CloudFormation şablonu kullanılarak master node ayağa kalktıktan sonra worker node otomatik olarak cluster'a katılır.

> **Alternatif:** Yerel cluster kurmakta sorun yaşıyorsanız tarayıcı üzerinden ücretsiz playground kullanabilirsiniz:  
> https://killercoda.com/playgrounds

### Cluster Durumunu Doğrulama

```bash
# Cluster'ın erişilebilir olup olmadığını ve kontrol düzlemi (control plane) bileşenlerini gösterir
kubectl cluster-info

# Tüm node'ları listeler; STATUS sütununda "Ready" yazması gerekir
kubectl get nodes
```

| Komut | Amaç |
|---|---|
| `kubectl cluster-info` | API server, CoreDNS gibi bileşenlerin adreslerini gösterir |
| `kubectl get nodes` | Node listesini ve hazırlık durumunu gösterir |

---

## Bölüm 2 – ServiceAccount

### ServiceAccount Nedir?

Kubernetes'te iki tür kimlik doğrulama mevcuttur:

1. **Kullanıcı hesapları (User Accounts):** İnsan kullanıcılar için. Kubernetes'in kendi User API'si yoktur; bu kimlikler dış sistemlerde (örn. sertifika, OIDC) yönetilir.
2. **Servis hesapları (Service Accounts):** **Pod içinde çalışan süreçler** için. Kubernetes API'sine erişmesi gereken uygulamalar bu kimliği kullanır.

Her namespace'de en az bir ServiceAccount bulunur: `default`. Bir Pod oluştururken ServiceAccount belirtmezseniz Kubernetes otomatik olarak `default` hesabını atar.

### Mevcut ServiceAccount'ları Listeleme

```bash
# Aktif namespace'deki (genellikle "default") ServiceAccount'ları listeler
kubectl get serviceaccount

# Kısa alias ile aynı komut
kubectl get sa

# Tüm namespace'lerdeki ServiceAccount'ları listeler (-A = --all-namespaces)
kubectl get sa -A
```

| Komut | Açıklama |
|---|---|
| `kubectl get sa` | Aktif namespace'deki SA listesi |
| `kubectl get sa -A` | Cluster genelinde tüm SA'lar |

### Pod Üzerinde ServiceAccount İnceleme

```bash
# nginx image'ından "myng" adında bir Pod oluşturur
kubectl run myng --image=nginx

# Pod'un tüm YAML tanımını gösterir; spec.serviceAccountName alanına dikkat edin
kubectl get pod myng -o yaml
```

Çıktıda `spec.serviceAccountName: default` satırını göreceksiniz. Kubernetes bu değeri siz belirtmediğinizde otomatik ekler.

### Yeni ServiceAccount Oluşturma

Aşağıdaki komut `mysa` adında bir ServiceAccount oluşturur:

```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: mysa
EOF
```

```bash
# Oluşturulan ServiceAccount'ları kontrol et
kubectl get sa

# "mysa" ServiceAccount'ının detaylı YAML tanımını görüntüle
kubectl get serviceaccount mysa -o yaml
```

> **Not:** Kubernetes v1.24+ sürümlerinde ServiceAccount token'ları artık otomatik olarak Secret olarak oluşturulmaz. Token almak için:
> ```bash
> kubectl create token mysa
> ```

---

## Bölüm 3 – RBAC Yetkilendirmesi

### RBAC Nedir?

**Role-Based Access Control (Rol Tabanlı Erişim Kontrolü)**, kullanıcıların veya süreçlerin hangi Kubernetes kaynaklarına ne tür işlemler yapabileceğini, organizasyondaki **rollere** göre belirleyen bir yetkilendirme modelidir.

RBAC; `rbac.authorization.k8s.io` API grubunu kullanır ve politikaları dinamik olarak yapılandırmanıza olanak tanır.

### Çalışma Dizini Oluşturma

```bash
# RBAC adında bir klasör oluşturur ve içine geçer
mkdir RBAC && cd RBAC
```

---

### API Nesneleri

RBAC dört temel nesne türü tanımlar:

| Nesne | Kapsam | Açıklama |
|---|---|---|
| **Role** | Namespace | Belirli bir namespace içinde izin tanımlar |
| **ClusterRole** | Cluster geneli | Tüm namespace'lerde veya cluster kaynaklarında izin tanımlar |
| **RoleBinding** | Namespace | Role veya ClusterRole'ü bir namespace'de bağlar |
| **ClusterRoleBinding** | Cluster geneli | ClusterRole'ü tüm cluster'da bağlar |

> **Önemli:** İzinler **eklemeli (additive)** çalışır — "deny" kuralı yoktur. Varsayılan olarak her şey yasaktır; izinler açıkça tanımlanarak verilir.

---

### Role ve ClusterRole

#### Role (Namespace Kapsamlı)

`Role`, yalnızca **belirli bir namespace** içinde geçerlidir. Oluşturulurken namespace belirtmek zorunludur.

**`myrole.yaml` dosyasını oluşturun:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default       # Bu rolün geçerli olduğu namespace
  name: pod-reader         # Rolün adı
rules:
- apiGroups: [""]          # "" çekirdek API grubunu ifade eder (Pod, Service, vb.)
  resources: ["pods"]      # Hangi kaynak türüne erişim verileceği
  verbs: ["get", "watch", "list"]  # İzin verilen işlemler
```

**Verb (işlem) açıklamaları:**

| Verb | HTTP Karşılığı | Açıklama |
|---|---|---|
| `get` | GET | Tekil kaynak okuma |
| `list` | GET (koleksiyon) | Kaynak listesini alma |
| `watch` | GET + watch | Değişiklikleri izleme (stream) |
| `create` | POST | Yeni kaynak oluşturma |
| `update` | PUT | Kaynağı tamamen güncelleme |
| `patch` | PATCH | Kaynağı kısmen güncelleme |
| `delete` | DELETE | Kaynak silme |

```bash
# Role'ü cluster'a uygular
kubectl apply -f myrole.yaml

# Mevcut Role'leri listeler
kubectl get role
```

---

#### ClusterRole (Cluster Geneli)

`ClusterRole`; namespace bağımsız çalışır ve şu durumlarda kullanılır:

- Tüm namespace'lerdeki kaynaklara erişim (örn. `kubectl get pods -A`)
- Cluster kapsamlı kaynaklar (Node, PersistentVolume, vb.)
- `/healthz` gibi non-resource endpoint'ler

**`myclusterrole.yaml` dosyasını oluşturun:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  # namespace belirtilmez — ClusterRole namespace kapsamı dışındadır
  name: secret-reader
rules:
- apiGroups: [""]
  # HTTP düzeyinde Secret nesnelerine erişim "secrets" kaynağı üzerinden sağlanır
  resources: ["secrets"]
  verbs: ["get", "watch", "list"]
```

```bash
# ClusterRole'ü cluster'a uygular
kubectl apply -f myclusterrole.yaml

# Tüm ClusterRole'leri listeler (Kubernetes'in yerleşik olanları dahil)
kubectl get clusterrole
```

> **İpucu:** `kubectl get clusterrole` çıktısında `system:` önekli çok sayıda Kubernetes yerleşik rolü göreceksiniz. Bunlar Kubernetes bileşenlerinin kendi iç izin yapılandırmalarıdır.

---

### RoleBinding ve ClusterRoleBinding

Rol tanımlamak tek başına yetmez; bir rolü kullanıcıya, gruba veya ServiceAccount'a **bağlamak** gerekir.

#### RoleBinding (Namespace Kapsamlı Bağlama)

`RoleBinding`, bir `Role` ya da `ClusterRole`'ü **belirli bir namespace içindeki** özneye (subject) bağlar.

**Bağlamadan önce yetkisiz erişimi test edin:**

```bash
# clarusway/kubectl image'ını kullanan bir test Pod'u oluşturur (içinde kubectl aracı mevcuttur)
kubectl run mypod --image=clarusway/kubectl

# Pod'un shell'ine bağlanır (-it: interaktif terminal, -- sh: çalıştırılacak komut)
kubectl exec -it mypod -- sh

# Mevcut kimliği sorgular
/ # kubectl auth whoami

# Pod listesi istenir — yetki olmadığı için hata alınır
/ # kubectl get pods
# Beklenen hata:
# Error from server (Forbidden): pods is forbidden:
# User "system:serviceaccount:default:default" cannot list resource "pods"
/ # exit
```

**`myrolebinding.yaml` dosyasını oluşturun:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default          # Bu binding'in geçerli olduğu namespace
subjects:
  # Bağlama yapılacak özne(ler) — birden fazla tanımlanabilir
  - kind: ServiceAccount
    name: default             # "default" ServiceAccount (büyük/küçük harf duyarlı)
    namespace: default
roleRef:
  # Hangi Role veya ClusterRole'ün bağlanacağı
  kind: Role                  # "Role" veya "ClusterRole" olabilir
  name: pod-reader            # Önceki adımda oluşturduğumuz role'ün adı
  apiGroup: rbac.authorization.k8s.io
```

```bash
# RoleBinding'i uygular
kubectl apply -f myrolebinding.yaml

# Mevcut RoleBinding'leri listeler
kubectl get rolebinding
```

**Bağlamadan sonra izinleri doğrulayın:**

```bash
kubectl exec -it mypod -- sh

# Artık Pod listesi alınabilir (sadece default namespace'de)
/ # kubectl get pods
# NAME    READY   STATUS    RESTARTS   AGE
# myng    1/1     Running   0          45m
# mypod   1/1     Running   0          26m

# Deployment listeleme — hâlâ yasak (Role sadece pods için tanımlı)
/ # kubectl get deployments
# Error from server (Forbidden): deployments.apps is forbidden

# Pod oluşturma — yasak (sadece get/list/watch izni var, create yok)
/ # kubectl run testpod --image=nginx
# Error from server (Forbidden): pods is forbidden: ... cannot create resource "pods"

# Diğer namespace'lerdeki Pod'ları listeleme — yasak (RoleBinding sadece default namespace'de geçerli)
/ # kubectl get pods -A
# Error from server (Forbidden): ... cannot list resource "pods" at the cluster scope

/ # exit
```

Bu sonuçlar RBAC'ın çalıştığını doğrular: yalnızca `default` namespace'de Pod okuma izni verildi.

---

#### ClusterRoleBinding (Cluster Geneli Bağlama)

`ClusterRoleBinding`, bir `ClusterRole`'ü tüm cluster genelinde geçerli kılar; namespace sınırı yoktur.

**Bağlamadan önce yetkisiz Pod oluşturun:**

**`kubepod.yaml` dosyasını oluşturun:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: kubepod
spec:
  serviceAccountName: mysa   # Bu Pod "mysa" ServiceAccount kimliğiyle çalışır
  containers:
    - name: kubepod
      image: clarusway/kubectl
```

```bash
# Pod'u oluşturur
kubectl apply -f kubepod.yaml

# Yetkisiz erişimi test et
kubectl exec -it kubepod -- sh

/ # kubectl auth whoami
/ # kubectl get secrets
# Error from server (Forbidden): secrets is forbidden: ...
/ # exit
```

**`myclusterrolebinding.yaml` dosyasını oluşturun:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-secrets-global
subjects:
  - kind: ServiceAccount
    name: mysa              # Önceki adımda oluşturduğumuz ServiceAccount
    namespace: default
roleRef:
  kind: ClusterRole
  name: secret-reader       # Tüm namespace'lerdeki Secret'lara okuma izni
  apiGroup: rbac.authorization.k8s.io
```

```bash
# ClusterRoleBinding'i uygular
kubectl apply -f myclusterrolebinding.yaml

# Mevcut ClusterRoleBinding'leri listeler
kubectl get clusterrolebinding
```

**Cluster geneli erişimi doğrulayın:**

```bash
kubectl exec -it kubepod -- sh

# Artık tüm namespace'lerdeki Secret'lar listelenebilir
/ # kubectl get secrets -A
# Tüm namespace'lerdeki secret listesi görüntülenir

/ # exit
```

---

### ServiceAccount Token Oluşturma

```bash
# Belirtilen ServiceAccount için geçici bir JWT token üretir
# Bu token, dış araçlardan API server'a kimlik doğrulaması için kullanılabilir
kubectl create token mysa
```

---

### RBAC Mimarisinin Özeti

```
ServiceAccount (mysa)
        │
        │ ← ClusterRoleBinding (read-secrets-global)
        │
        ▼
  ClusterRole (secret-reader)
  rules:
    - secrets → get, watch, list
    - tüm namespace'lerde geçerli

ServiceAccount (default)
        │
        │ ← RoleBinding (read-pods) [sadece "default" namespace'de]
        │
        ▼
  Role (pod-reader)
  rules:
    - pods → get, watch, list
    - yalnızca "default" namespace'de geçerli
```

---

## Kaynaklar

- [ServiceAccount Yapılandırma – Kubernetes Resmi Dokümantasyonu](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
- [RBAC Yetkilendirmesi – Kubernetes Resmi Dokümantasyonu](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
