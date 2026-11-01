export const PASSWORD_COMPLEXITY_MESSAGE =
  '密码长度不少于10位，且至少包含大写字母、小写字母、数字、特殊符号中的3类'
export const PASSWORD_USERNAME_MESSAGE = '密码不得包含账号用户名'

const hasUppercase = (value: string) => /[A-Z]/.test(value)
const hasLowercase = (value: string) => /[a-z]/.test(value)
const hasDigit = (value: string) => /\d/.test(value)
const hasSpecialChar = (value: string) => /[^A-Za-z0-9]/.test(value)

export const isPasswordComplexEnough = (value: string): boolean => {
  const password = String(value || '')
  if (password.length < 10) {
    return false
  }

  const categoryCount = [
    hasUppercase(password),
    hasLowercase(password),
    hasDigit(password),
    hasSpecialChar(password)
  ].filter(Boolean).length

  return categoryCount >= 3
}

export const doesPasswordContainUsername = (password: string, username?: string): boolean => {
  const normalizedPassword = String(password || '').toLowerCase()
  const normalizedUsername = String(username || '').trim().toLowerCase()
  if (!normalizedPassword || !normalizedUsername) {
    return false
  }
  return normalizedPassword.includes(normalizedUsername)
}

export const isPasswordPolicyValid = (password: string, username?: string): boolean => {
  return isPasswordComplexEnough(password) && !doesPasswordContainUsername(password, username)
}
