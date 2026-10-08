import { createCipheriv, createDecipheriv, randomBytes } from 'node:crypto'
import { chmodSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'

interface EncryptedValue {
  ciphertext: string
  iv: string
  tag: string
}

function loadEncryptionKey(): Buffer {
  const configuredKey = process.env.CREDENTIAL_ENCRYPTION_KEY
  if (configuredKey) {
    const encoding = /^[a-f0-9]{64}$/i.test(configuredKey) ? 'hex' : 'base64'
    const key = Buffer.from(configuredKey, encoding)
    if (key.length !== 32) throw new Error('CREDENTIAL_ENCRYPTION_KEY must decode to exactly 32 bytes')
    return key
  }

  const keyPath = resolve(process.env.CREDENTIAL_KEY_PATH ?? 'storage/credentials.key')
  mkdirSync(dirname(keyPath), { recursive: true })
  if (!existsSync(keyPath)) {
    writeFileSync(keyPath, randomBytes(32), { mode: 0o600 })
  }
  chmodSync(keyPath, 0o600)
  const key = readFileSync(keyPath)
  if (key.length !== 32) throw new Error(`Credential key at ${keyPath} must contain exactly 32 bytes`)
  return key
}

const encryptionKey = loadEncryptionKey()

export function encryptCredential(value: string): EncryptedValue {
  const iv = randomBytes(12)
  const cipher = createCipheriv('aes-256-gcm', encryptionKey, iv)
  const ciphertext = Buffer.concat([cipher.update(value, 'utf8'), cipher.final()])
  return {
    ciphertext: ciphertext.toString('base64'),
    iv: iv.toString('base64'),
    tag: cipher.getAuthTag().toString('base64'),
  }
}

export function decryptCredential(value: EncryptedValue): string {
  const decipher = createDecipheriv('aes-256-gcm', encryptionKey, Buffer.from(value.iv, 'base64'))
  decipher.setAuthTag(Buffer.from(value.tag, 'base64'))
  return Buffer.concat([
    decipher.update(Buffer.from(value.ciphertext, 'base64')),
    decipher.final(),
  ]).toString('utf8')
}
