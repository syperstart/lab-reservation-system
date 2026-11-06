// 全站唯一的用户状态（单数据源，不引入 Pinia）
// 设计原则：任何组件都只从这里读用户信息，不各自读 localStorage 拼数据，避免多处不一致。
// 头部、个人中心、登录、登出都围绕这个响应式对象 + 三个方法协作。
import { reactive } from 'vue'

// localStorage 里存用户信息的键名（与 token 分开存）
const STORAGE_KEY = 'user'

// 全局唯一用户状态：reactive 包一层，组件里读到的永远是「最新值」，改了自动刷新视图
export const userState = reactive({
  id: 0,        // 用户主键
  username: '', // 登录账号（个人中心只读展示）
  name: '',     // 名称 / 昵称（个人中心可改）
  role: '',     // 角色：admin / student（只读展示）
  email: '',    // 邮箱（可改）
  phone: '',    // 手机号（可改）
  avatar: '',   // 头像地址（可为空，空时用姓名首字的圆形色块兜底）
})

// 把当前 userState 持久化到 localStorage（每次写入/更新都调用）
function persist() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...userState }))
}

// 应用启动时调用：从 localStorage 恢复上次登录的用户信息
// 这样刷新页面、重新进入站点，头部和头像都不会「变空白」
function restore() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const data = JSON.parse(raw)
      Object.assign(userState, data) // 用存下来的数据覆盖进响应式对象
    }
  } catch (e) {
    // 数据损坏读不出来就忽略，当作未登录处理
  }
}

// 整体写入：登录成功 或 拉取个人信息后调用
// 后端返回的用户对象字段名可能不同，这里做防御性取值，缺字段也不报错
export function setUser(data: any) {
  if (!data) return
  userState.id = data.id ?? userState.id
  userState.username = data.username ?? ''
  userState.name = data.name ?? ''
  userState.role = data.role ?? ''
  userState.email = data.email ?? ''
  userState.phone = data.phone ?? ''
  userState.avatar = data.avatar ?? ''
  persist() // 写入即持久化
}

// 局部更新：只改其中几个字段（比如只改头像），同样持久化
export function updateUser(patch: any) {
  Object.assign(userState, patch)
  persist()
}

// 退出登录：清掉内存状态 + 本地存储（用户信息 + token 一起清）
export function clearUser() {
  Object.assign(userState, {
    id: 0,
    username: '',
    name: '',
    role: '',
    email: '',
    phone: '',
    avatar: '',
  })
  localStorage.removeItem(STORAGE_KEY) // 清用户信息
  localStorage.removeItem('token')    // 清登录令牌（顺手一起清，避免串号）
}

// 取「姓名首字」：无头像时显示在圆形色块里，避免空白或破图
// 姓名没有就退而用账号，再没有用问号；统一转大写更整齐
export function userInitial(): string {
  const base = userState.name || userState.username || '?'
  return base.trim().charAt(0).toUpperCase()
}

// 模块加载即尝试恢复（等价于应用启动恢复）
restore()
