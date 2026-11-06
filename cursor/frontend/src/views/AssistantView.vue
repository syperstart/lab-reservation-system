<script setup lang="ts">
// ==================== AI 智能助手对话页 ====================
// 职责：展示对话气泡、发送消息，对接后端 POST /api/ai/chat。
// 说明：
//  1) 进入页面默认推一条欢迎语（助手气泡）
//  2) 发送时把「本轮用户消息之前」的对话历史（最多 10 条）传给后端，让模型理解上下文
//  3) 成功 → 追加助手回复；失败 → 拦截器已弹错，这里再补一条「回答失败，请重试」的气泡
//  4) 每次消息变化后自动滚动到底部
// ========================================================

import { ref, nextTick, onMounted, watch } from 'vue'
// 统一请求工具：自动带 token、统一错误提示（失败时拦截器已弹 ElMessage.error）
import request from '@/utils/request'

// 一条对话气泡的数据结构
interface ChatItem {
  // 角色：user=用户（右对齐蓝底白字）/ assistant=助手（左对齐灰底深字）
  role: 'user' | 'assistant'
  // 气泡文字内容
  content: string
  // 是否参与历史上下文：欢迎语、失败提示等「占位气泡」不计入 history
  inHistory: boolean
}

// 欢迎语：进入页面默认显示，帮用户快速了解助手能答什么、不能答什么
const WELCOME =
  '你可以问我关于预约流程或取消预约的问题。具体的实验室列表、设备信息及开放时间，请前往「实验室列表」页面查看。'

// 会话缓存键：同一标签页内切换菜单 / 刷新页面后恢复上次对话，不丢失
const SAVED_KEY = 'assistant_chat'

// 从 sessionStorage 读取上次对话；没有或数据损坏则回退到欢迎语
function loadSavedMessages(): ChatItem[] {
  try {
    const raw = sessionStorage.getItem(SAVED_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed) && parsed.length > 0) return parsed as ChatItem[]
    }
  } catch (e) {
    // 解析失败就忽略，回到默认欢迎语
  }
  return [{ role: 'assistant', content: WELCOME, inHistory: false }]
}

// 对话消息列表：优先恢复上次对话（切换菜单不再清空）
const messages = ref<ChatItem[]>(loadSavedMessages())

// 每次消息变化都写回 sessionStorage（deep 监听，push 也能触发）
watch(
  messages,
  () => sessionStorage.setItem(SAVED_KEY, JSON.stringify(messages.value)),
  { deep: true },
)

// 输入框内容（v-model 双向绑定）
const input = ref('')
// 发送中标记：true 时按钮禁用并显示「发送中…」，同时禁止重复发送
const loading = ref(false)
// 对话滚动容器的 DOM 引用，用于自动滚到底部
const listRef = ref<HTMLElement>()

// 自动滚动到底部：等 DOM 更新（nextTick）后把 scrollTop 设为 scrollHeight
async function scrollToBottom() {
  await nextTick()
  if (listRef.value) {
    listRef.value.scrollTop = listRef.value.scrollHeight
  }
}

// 发送消息
async function send() {
  // 去掉首尾空格；空内容直接不发送
  const text = input.value.trim()
  // 空内容、或正在发送中，都直接返回（防止重复发送）
  if (!text || loading.value) return

  // 1) 先把用户消息 push 进消息列表（右对齐气泡）
  messages.value.push({ role: 'user', content: text, inHistory: true })
  // 2) 清空输入框、进入加载态
  input.value = ''
  loading.value = true
  scrollToBottom() // 用户气泡 + 底部「正在思考…」气泡出现后滚到底

  try {
    // 3) 组装 history：只取「本轮用户消息之前」的真实对话，最多保留最近 10 条
    //    先过滤掉欢迎语/失败提示等占位气泡（inHistory=false），
    //    再去掉刚 push 的本轮用户消息（slice(0, -1)），最后只留最近 10 条
    const history = messages.value
      .filter((m) => m.inHistory)
      .slice(0, -1)
      .slice(-10)
      .map(({ role, content }) => ({ role, content }))

    // 4) 调后端：拦截器会自动带 token；成功后返回 { reply: string }
    const data: any = await request.post('/ai/chat', { message: text, history })
    // 5) 成功后追加助手回复（左对齐气泡）
    messages.value.push({ role: 'assistant', content: data.reply, inHistory: true })
  } catch (e) {
    // 6) 失败：拦截器已弹错误提示；这里只在气泡区补一条失败提示，不打断后续对话
    messages.value.push({ role: 'assistant', content: '回答失败，请重试', inHistory: false })
  } finally {
    // 7) 无论成败都关闭加载态，并滚到底部
    loading.value = false
    scrollToBottom()
  }
}

// 输入框键盘处理：Enter 发送（Shift+Enter 保留换行）
function onEnter(e: Event | KeyboardEvent) {
  // el-input 的 keydown 事件类型是 Event | KeyboardEvent，这里统一按 KeyboardEvent 处理
  const evt = e as KeyboardEvent
  // 中文输入法组词中按 Enter 是「选字」：isComposing 或 keyCode 229，此时不拦截也不发送
  if (evt.isComposing || evt.keyCode === 229) return
  // 阻止默认「换行」行为，改为发送
  evt.preventDefault()
  send()
}

// 挂载后滚到底部（欢迎语可能超出一屏）
onMounted(() => {
  scrollToBottom()
})
</script>

<template>
  <div class="assistant-page">
    <!-- 页面标题栏 -->
    <div class="chat-header">
      <h2 class="chat-title">AI智能助手</h2>
      <p class="chat-sub">预约流程、取消预约等使用问题都可以问我</p>
    </div>

    <!-- 对话区：可滚动 -->
    <div ref="listRef" class="chat-body">
      <!-- 逐条渲染气泡：role 决定左右对齐与配色 -->
      <div
        v-for="(m, i) in messages"
        :key="i"
        class="msg-row"
        :class="m.role === 'user' ? 'is-user' : 'is-assistant'"
      >
        <div class="bubble">{{ m.content }}</div>
      </div>

      <!-- 加载中占位气泡：显示「正在思考…」 -->
      <div v-if="loading" class="msg-row is-assistant">
        <div class="bubble thinking">正在思考…</div>
      </div>
    </div>

    <!-- 输入区：固定在底部，textarea + 发送按钮 -->
    <div class="chat-input">
      <el-input
        v-model="input"
        class="input-box"
        type="textarea"
        :rows="2"
        placeholder="请输入您的问题，如：怎么预约实验室"
        @keydown.enter.exact="onEnter"
      />
      <el-button
        class="send-btn"
        type="primary"
        :loading="loading"
        @click="send"
      >
        {{ loading ? '发送中…' : '发送' }}
      </el-button>
    </div>
  </div>
</template>

<style scoped>
/* 整页卡片：占满页面滚动区高度，纵向 flex（标题栏 + 对话区 + 输入区） */
.assistant-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  box-shadow: 0 6px 20px -12px rgba(31, 45, 80, 0.18);
  overflow: hidden; /* 圆角 + 内部滚动时，内容不溢出圆角 */
}

/* 标题栏 */
.chat-header {
  padding: 16px 20px 12px;
  border-bottom: 1px solid var(--line);
}
.chat-title {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: var(--text-1);
}
.chat-sub {
  margin: 4px 0 0;
  font-size: 12.5px;
  color: var(--text-3);
}

/* 对话区：占满剩余高度，纵向 flex + 纵向滚动 */
.chat-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 20px;
}

/* 单条消息行：整行 flex，用 justify-content 决定气泡靠左还是靠右 */
.msg-row {
  display: flex;
  width: 100%;
}
.msg-row.is-assistant {
  justify-content: flex-start; /* 助手靠左 */
}
.msg-row.is-user {
  justify-content: flex-end; /* 用户靠右 */
}

/* 气泡通用样式 */
.bubble {
  max-width: 70%;
  padding: 8px 12px;
  border-radius: 8px;
  line-height: 1.6;
  font-size: 14px;
  white-space: pre-wrap; /* 保留换行 */
  word-break: break-word; /* 长文本自动折行，避免撑破气泡 */
}
/* 助手气泡：左对齐，浅灰底 + 深色字 */
.is-assistant .bubble {
  background: #f4f4f5;
  color: #1f2329;
}
/* 用户气泡：右对齐，蓝色底 + 白色字 */
.is-user .bubble {
  background: rgba(64, 158, 255, 0.9);
  color: #fff;
}

/* 正在思考占位气泡：淡一点 + 呼吸动画 */
.thinking {
  color: #6b7484;
  animation: thinking-pulse 1.4s ease-in-out infinite;
}
@keyframes thinking-pulse {
  0%,
  100% {
    opacity: 0.5;
  }
  50% {
    opacity: 1;
  }
}

/* 输入区：固定在底部（flex 布局最后一项），上方浅色分隔线 */
.chat-input {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 12px 20px 16px;
  border-top: 1px solid var(--line);
  background: #fff;
}
/* 输入框占满剩余宽度 */
.input-box {
  flex: 1;
}
/* 发送按钮不收缩 */
.send-btn {
  flex-shrink: 0;
}
</style>
