export type TradingMode = 'PAPER' | 'TESTNET' | 'LIVE'
export type BotState = 'STOPPED' | 'RUNNING' | 'PAUSED' | 'EMERGENCY'

export interface Health { status: string; trading_mode: TradingMode; market: string; version: string }
export interface BotStatus { state: BotState; trading_mode: TradingMode; market: string; emergency: boolean }
