import axios from 'axios'

const API_URL = window.ENV?.API_URL ?? process.env.REACT_APP_API_URL ?? ""

const api = axios.create({ baseURL: API_URL })

api.interceptors.request.use((config) => {
    const token = sessionStorage.getItem("accessToken")
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

api.interceptors.response.use(
    response => response,
    error => {
        if (error.response?.status === 401) {
            sessionStorage.removeItem("accessToken")
            sessionStorage.removeItem("newUserId")
            sessionStorage.removeItem("isAdmin")
        }
        return Promise.reject(error)
    }
)

export default api
