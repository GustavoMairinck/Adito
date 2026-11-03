<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Loader2, LogIn } from 'lucide-vue-next'
import fapesGovLogo from '../assets/fapes-goves-20anos.png'
import brandIcon from '@/common/assets/brand-icon.png'
import { useAuth } from '@/modules/auth/composables/useAuth'

const route = useRoute()
const router = useRouter()
const { login } = useAuth()

const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true

  try {
    // Usando credenciais reais do admin conforme o .env
    await login('admin', 'fdb21104f08e23b3ce747f0758450c4e')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/chat'
    router.push(redirect)
  } catch (err: any) {
    error.value = err.message || 'Erro ao realizar login.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="relative min-h-screen flex flex-col items-center justify-center overflow-hidden font-sans selection:bg-blue-400/30">

    <!-- === CONTRASTING GRADIENT BACKGROUND BASE === -->
    <div class="absolute inset-0 bg-gradient-to-br from-[#e2e8f0] via-[#f8fafc] to-[#e2e8f0]"></div>

    <!-- === CONCENTRIC PULSE WAVES === -->
    <div class="absolute inset-0 pointer-events-none overflow-hidden">
      <!-- Ring 1: outer -->
      <div class="pulse-ring ring-1"></div>
      <!-- Ring 2: middle -->
      <div class="pulse-ring ring-2"></div>
      <!-- Ring 3: inner -->
      <div class="pulse-ring ring-3"></div>
    </div>

    <!-- === RADIAL CENTER GLOW (neutral silver-blue) === -->
    <div class="absolute inset-0 pointer-events-none"
      style="background: radial-gradient(circle at 50% 45%, rgba(255, 255, 255, 0.9) 0%, rgba(210, 225, 255, 0.5) 35%, transparent 70%)">
    </div>

    <!-- === NOISE TEXTURE OVERLAY (gray rough texture) === -->
    <div class="noise absolute inset-0 pointer-events-none opacity-[0.15] mix-blend-overlay"></div>

    <!-- === SUBTLE DOT GRID === -->
    <div
      class="absolute inset-0 z-0 opacity-[0.22] pointer-events-none"
      style="background-image: radial-gradient(#a0afc0 1.2px, transparent 1.2px); background-size: 36px 36px;"
    ></div>

    <!-- Main Content -->
    <div
      v-motion="{
        initial: { opacity: 0, scale: 0.96, y: 15 },
        enter: { opacity: 1, scale: 1, y: 0, transition: { duration: 900, ease: 'easeOut' } }
      }"
      class="relative z-10 w-full max-w-md px-8 flex flex-col items-center -mt-28 sm:-mt-36"
    >
      <!-- Logo ORACULO-ESX: com shimmer passando exatamente no ícone e na fonte -->
      <div class="mb-6 flex flex-col items-center justify-center gap-3 cursor-default select-none relative px-4 py-2 sm:flex-row">
        <!-- Ícone -->
        <div class="relative">
          <div class="mix-blend-multiply">
            <img
              :src="brandIcon"
              alt="Ícone ORACULO-ESX"
              class="h-16 sm:h-20 w-auto object-contain"
            />
          </div>
          <!-- Ícone brilhante sobreposto com máscara para o shimmer -->
          <img
            :src="brandIcon"
            aria-hidden="true"
            class="absolute inset-0 h-16 sm:h-20 w-auto object-contain shimmer-mask"
          />
        </div>
        <!-- Nome ORACULO-ESX -->
        <div class="relative inline-block text-3xl sm:text-4xl font-bold tracking-tight shimmer-text">
          <span class="absolute -top-[18px] left-0 flex items-center justify-center rounded-full border border-slate-500/50 px-[5px] py-[2px] text-[8px] font-bold uppercase tracking-[0.1em] text-slate-500/80 leading-none select-none whitespace-nowrap">
            beta
          </span>
          ORACULO-ESX
        </div>
      </div>

      <!-- Textos -->
      <div class="text-center mb-10">
        <p class="text-[10px] sm:text-xs font-bold uppercase tracking-[0.25em] text-slate-500 mb-4">Acesso ao Ambiente</p>
        <h1 class="text-3xl sm:text-4xl font-semibold text-slate-900 tracking-tight leading-tight mb-5 whitespace-nowrap">
          Decisões guiadas por dados.
        </h1>
        <p class="text-slate-600 text-sm sm:text-[15px] leading-relaxed whitespace-nowrap mx-auto">
          Bem-vindo de volta! Converse sobre estratégia com <span class="font-semibold text-[#2455a7]">seus dados</span>.
        </p>
      </div>

      <transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0 translate-y-2"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div v-if="error" class="w-full mb-6 rounded-2xl border border-red-200 bg-red-50/80 backdrop-blur px-5 py-4 text-sm text-red-700 shadow-sm text-center">
          {{ error }}
        </div>
      </transition>

      <!-- Formulário de Login -->
      <form @submit.prevent="handleLogin" class="w-full flex flex-col gap-4">
        <button
          type="submit"
          :disabled="loading"
          class="group relative flex w-full items-center justify-center gap-3 rounded-xl bg-[#2455a7] px-8 py-3.5 text-[15px] font-medium text-white shadow-lg shadow-blue-900/40 transition-all duration-300 hover:bg-[#1d4588] hover:shadow-blue-900/60 hover:shadow-xl hover:-translate-y-[1px] disabled:cursor-not-allowed disabled:opacity-70 disabled:hover:translate-y-0"
        >
          <Loader2 v-if="loading" class="h-5 w-5 animate-spin" />
          <LogIn v-else class="h-5 w-5 transition-transform duration-300 group-hover:-translate-x-1" />
          <span>Logar no programa</span>
        </button>
      </form>
    </div>

    <!-- Footer: FAPES / GOV -->
    <div class="absolute bottom-6 sm:bottom-10 w-full px-6 flex flex-col items-center justify-center z-10 pointer-events-none">
      <div
        v-motion="{
          initial: { opacity: 0, y: 10 },
          enter: { opacity: 1, y: 0, transition: { duration: 800, delay: 300 } }
        }"
        class="max-w-[380px] w-full flex flex-col items-center gap-4 pointer-events-auto"
      >
        <img
          :src="fapesGovLogo"
          alt="FAPES e Governo do Estado do Espírito Santo"
          class="h-auto w-full object-contain mix-blend-multiply opacity-80 hover:opacity-100 transition-all duration-300"
        />
        <p class="text-[10px] sm:text-xs text-slate-500 font-medium tracking-wide">
          FAPES © {{ new Date().getFullYear() }} · Todos os direitos reservados
        </p>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* ===== CONCENTRIC PULSE WAVES (Steel / Metallic Light) ===== */
.pulse-ring {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  will-change: transform, opacity;
  left: 50%;
  top: 50%;
}

.ring-1 {
  width: 100vw;
  height: 100vw;
  max-width: 1200px;
  max-height: 1200px;
  background: rgba(255, 255, 255, 0.6);
  animation: pulseWaveOuter 5s ease-in-out infinite alternate;
}

.ring-2 {
  width: 80vw;
  height: 80vw;
  max-width: 900px;
  max-height: 900px;
  background: rgba(220, 235, 255, 0.7);
  animation: pulseWaveInner 4s ease-in-out infinite alternate-reverse;
}

.ring-3 {
  width: 60vw;
  height: 60vw;
  max-width: 700px;
  max-height: 700px;
  background: rgba(180, 215, 255, 0.8);
  animation: pulseWaveCore 3.5s ease-in-out infinite alternate;
}

@keyframes pulseWaveOuter {
  0% {
    transform: translate(-50%, -50%) scale(1.1);
    opacity: 0.4;
  }
  100% {
    transform: translate(-50%, -50%) scale(1.6);
    opacity: 0.8;
  }
}

@keyframes pulseWaveInner {
  0% {
    transform: translate(-50%, -50%) scale(0.9);
    opacity: 0.5;
  }
  100% {
    transform: translate(-50%, -50%) scale(1.4);
    opacity: 0.9;
  }
}

@keyframes pulseWaveCore {
  0% {
    transform: translate(-50%, -50%) scale(0.7);
    opacity: 0.6;
  }
  100% {
    transform: translate(-50%, -50%) scale(1.2);
    opacity: 1;
  }
}

/* ===== NOISE TEXTURE ===== */
.noise {
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
  background-size: 180px 180px;
  background-repeat: repeat;
}

/* ===== SHIMMER TEXT & ICON MASK ===== */
.shimmer-text {
  background: linear-gradient(
    100deg,
    #0f172a 40%,
    #94a3b8 50%,
    #0f172a 60%
  );
  background-size: 250% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  animation: shimmerAnim 8s infinite;
  animation-delay: 0.2s;
}

.shimmer-mask {
  filter: brightness(0) invert(1) drop-shadow(0 0 6px rgba(255,255,255,0.6));
  -webkit-mask-image: linear-gradient(
    100deg,
    transparent 40%,
    black 50%,
    transparent 60%
  );
  mask-image: linear-gradient(
    100deg,
    transparent 40%,
    black 50%,
    transparent 60%
  );
  -webkit-mask-size: 250% 100%;
  mask-size: 250% 100%;
  animation: shimmerAnim 8s infinite;
  animation-delay: 0.2s;
}

@keyframes shimmerAnim {
  0% { 
    background-position: 150% 0; 
    -webkit-mask-position: 150% 0; 
    mask-position: 150% 0; 
  }
  20% { 
    background-position: -50% 0; 
    -webkit-mask-position: -50% 0; 
    mask-position: -50% 0; 
  }
  100% { 
    background-position: -50% 0; 
    -webkit-mask-position: -50% 0; 
    mask-position: -50% 0; 
  }
}
</style>
