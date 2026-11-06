// 1. 引入 axios 和 Element Plus 的提示框
import axios from 'axios'
import { ElMessage } from 'element-plus'

// 2. 创建一个「公共请求工具」request
//    以后所有和后端打交道的地方都用它，不用每次写 http://127.0.0.1:8000
const request = axios.create({
  baseURL: '/api',   // 所有请求自动加 /api 前缀（配合 vite 代理转发到后端）
  timeout: 10000,    // 超过 10 秒没结果就当作超时
})

// 3. 请求拦截器：每次「发出请求之前」都会自动执行
request.interceptors.request.use((config) => {
  // 从浏览器存储里取出登录时存下的 token
  const token = localStorage.getItem('token')
  // 如果有 token，就放进请求头，后端才能知道「你是谁、是否已登录」
  if (token) {
    config.headers.Authorization = 'Bearer ' + token
  }
  return config  // 一定要把 config 还回去，否则请求发不出去
})

// 4. 响应拦截器：每次「收到后端返回」之后都会自动执行
request.interceptors.response.use(
  // —— 情况一：请求成功回来了（HTTP 状态码是 2xx，比如 200）——
  (response) => {
    // 后端统一返回 { code, message, data } 这种格式
    const body = response.data
    // code 不是 200，说明业务出错了（比如「账号或密码错误」），弹提示
    if (body.code !== 200) {
      ElMessage.error(body.message || '请求失败')
      // 抛出错误，让调用它的地方进入 catch
      return Promise.reject(new Error(body.message))
    }
    // code 是 200，把真正的数据 body.data 返回给调用方
    return body.data
  },
  // —— 情况二：请求失败（401 未登录 / 500 服务器错 / 断网等）——
  (error) => {
    // 401 表示没登录或登录过期了
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token')
      ElMessage.error('登录已过期，请重新登录')
      window.location.href = '/login'
    } else {
      // 其它错误：优先显示后端给的提示，没有就给一句通用提示
      let msg = '网络错误，请稍后重试'
      if (error.response && error.response.data && error.response.data.message) {
        msg = error.response.data.message
      }
      ElMessage.error(msg)
    }
    return Promise.reject(error)
  },
)

// 5. 导出，别的文件 import request from '@/utils/request' 就能用
export default request
