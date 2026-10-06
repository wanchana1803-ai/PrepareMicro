/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "ssd1306.h"
#include "fonts.h"
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
ADC_HandleTypeDef hadc1;

I2C_HandleTypeDef hi2c1;

TIM_HandleTypeDef htim1;
TIM_HandleTypeDef htim5;

UART_HandleTypeDef huart2;

/* USER CODE BEGIN PV */
#define MOTOR_MAX_RPM     1500
#define ENCODER_PPR       100
// --- ตัวแปร PWM & ADC ---
uint32_t adc_val = 0;
uint32_t freq_hz = 500;
uint16_t duty_val = 20;
uint32_t arr_val = 1999;
uint32_t ccr_val = 400;
float period_ms = 2.00f;
float rpm_disp = 300.0f;
uint8_t vr_pct = 0;
// --- ตัวแปร Encoder & ทิศทางหมุน (CW / CCW / STOP) ---
uint32_t current_count = 0;
uint32_t prev_count = 0;
int32_t diff_count = 0;
char dir_str[6] = "CW";      // แสดง CW, CCW, หรือ STOP
// --- ตัวจับเวลา ---
uint32_t last_adc_tick = 0;
uint32_t last_enc_tick = 0;
uint32_t last_oled_tick = 0;
char disp_str[32];
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_USART2_UART_Init(void);
static void MX_TIM1_Init(void);
static void MX_I2C1_Init(void);
static void MX_TIM5_Init(void);
static void MX_ADC1_Init(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */
uint32_t Read_ADC_Filtered(void)
{
    uint32_t sum = 0;
    for (int i = 0; i < 8; i++) // สุ่มอ่าน 8 ครั้งหาค่าเฉลี่ย
    {
        HAL_ADC_Start(&hadc1);
        if (HAL_ADC_PollForConversion(&hadc1, 5) == HAL_OK)
        {
            sum += HAL_ADC_GetValue(&hadc1); // อ่านค่าจาก PA4 (Channel 4)
        }
        HAL_ADC_Stop(&hadc1);
    }
    return sum / 8; // ได้ค่า adc_val ช่วง 0 - 4095
}
// ระบบ I2C Auto-Recovery ป้องกันจอค้างจากสัญญาณรบกวนของมอเตอร์
void OLED_CheckAndRecoverI2C(void)
{
    if (hi2c1.State != HAL_I2C_STATE_READY || hi2c1.ErrorCode != HAL_I2C_ERROR_NONE)
    {
        __HAL_RCC_I2C1_FORCE_RESET();
        HAL_Delay(2);
        __HAL_RCC_I2C1_RELEASE_RESET();
        HAL_I2C_Init(&hi2c1);
    }
}
// ฟังก์ชันวาดแถบ Progress Bar
void OLED_DrawBar(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint8_t pct)
{
    if (pct > 100) pct = 100;
    ssd1306_DrawRectangle(x, y, w, h, White);
    uint8_t fill_w = (uint8_t)(((uint16_t)(w - 4) * pct) / 100);
    for (uint8_t i = 2; i < h - 2; i++)
    {
        if (fill_w > 0)
        {
            ssd1306_DrawLine(x + 2, y + i, x + 2 + fill_w, y + i, White);
        }
    }
}
/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_USART2_UART_Init();
  MX_TIM1_Init();
  MX_I2C1_Init();
  MX_TIM5_Init();
  MX_ADC1_Init();
  /* USER CODE BEGIN 2 */
   // 1. ตั้งค่า Timer Preload
  // 1. ตั้งค่า Timer Preload
    __HAL_TIM_ENABLE_OCxPRELOAD(&htim1, TIM_CHANNEL_1);
    htim1.Instance->CR1 |= TIM_CR1_ARPE;
    // 2. เริ่มต้น PWM
    __HAL_TIM_SET_AUTORELOAD(&htim1, 1999);
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, 400);
    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
    // 3. เริ่มต้นตัวนับ Encoder (htim5 ขา PA0/PA1) 👈 เพิ่มบรรทัดนี้
    HAL_TIM_Encoder_Start(&htim5, TIM_CHANNEL_ALL);
    // 4. เริ่มต้นหน้าจอ OLED
    HAL_Delay(100);
    ssd1306_Init();
    ssd1306_Fill(Black);
    ssd1306_SetCursor(10, 20);
    ssd1306_WriteString("OLED SYSTEM OK", Font_7x10, White);
    ssd1306_SetCursor(10, 36);
    ssd1306_WriteString("We are love WRA.", Font_7x10, White);
    ssd1306_UpdateScreen();
    HAL_Delay(500);
   /* USER CODE END 2 */
  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
      while (1)
      {
    /* USER CODE END WHILE */

    	  /* USER CODE BEGIN 3 */
    	     // -------------------------------------------------------------------------
    	     // 1. อ่านค่า ADC (PA4 / A2) และคำนวณ Freq + Duty ทุก 30 ms
    	     // -------------------------------------------------------------------------
    	     if (HAL_GetTick() - last_adc_tick >= 30)
    	     {
    	         last_adc_tick = HAL_GetTick();
    	         adc_val = Read_ADC_Filtered();
    	         vr_pct = (uint8_t)(((uint32_t)adc_val * 100) / 4095);
    	         if (vr_pct > 100) vr_pct = 100;
    	         freq_hz = 500 + (((uint32_t)adc_val * 700) / 4095);
    	         duty_val = 20 + (uint16_t)(((uint32_t)adc_val * 60) / 4095);
    	         if (duty_val > 80) duty_val = 80;
    	         arr_val = (1000000UL / freq_hz) - 1;
    	         ccr_val = ((arr_val + 1) * (uint32_t)duty_val) / 100;
    	         __HAL_TIM_SET_AUTORELOAD(&htim1, arr_val);
    	         __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, ccr_val);
    	         period_ms = 1000.0f / (float)freq_hz;
    	     }
    	     // -------------------------------------------------------------------------
    	     // 2. คำนวณความเร็วรอบ (RPM) และทิศทางหมุน (CW / CCW) ทุก 100 ms 👈 เพิ่มส่วนนี้
    	     // -------------------------------------------------------------------------
    	     if (HAL_GetTick() - last_enc_tick >= 100)
    	     {
    	         uint32_t dt = HAL_GetTick() - last_enc_tick;
    	         last_enc_tick = HAL_GetTick();
    	         current_count = __HAL_TIM_GET_COUNTER(&htim5);
    	         diff_count = (int32_t)(current_count - prev_count);
    	         prev_count = current_count;
    	         // มีสัญญาณหมุนจาก Encoder จริง (กรองสัญญาณรบกวน threshold > 5)
    	         if (abs(diff_count) > 5)
    	         {
    	             if (diff_count > 0) strcpy(dir_str, "CW");
    	             else strcpy(dir_str, "CCW");
    	             rpm_disp = ((float)abs(diff_count) * 60000.0f) / ((4.0f * ENCODER_PPR) * (float)dt);
    	         }
    	         else
    	         {
    	             // คำนวณจาก Duty Cycle (ฐาน 1500 RPM)
    	             if (duty_val > 0)
    	             {
    	                 strcpy(dir_str, "CW");
    	                 rpm_disp = ((float)duty_val * (float)MOTOR_MAX_RPM) / 100.0f;
    	             }
    	             else
    	             {
    	                 strcpy(dir_str, "STOP");
    	                 rpm_disp = 0.0f;
    	             }
    	         }
    	     }
    	     // -------------------------------------------------------------------------
    	     // 3. รีเฟรชหน้าจอ OLED ทุก 150 ms
    	     // -------------------------------------------------------------------------
    	     if (HAL_GetTick() - last_oled_tick >= 150)
    	     {
    	         last_oled_tick = HAL_GetTick();
    	         OLED_CheckAndRecoverI2C();
    	         ssd1306_Fill(Black);
    	         // บรรทัดที่ 1: Header
    	         ssd1306_SetCursor(10, 0);
    	         ssd1306_WriteString("We are love WRA.", Font_7x10, White);
    	         // บรรทัดที่ 2: ความถี่ & คาบเวลา
    	         uint32_t p_int = (uint32_t)period_ms;
    	         uint32_t p_dec = (uint32_t)((period_ms - (float)p_int) * 100.0f);
    	         sprintf(disp_str, "F:%4luHz T:%lu.%02lums", freq_hz, p_int, p_dec);
    	         ssd1306_SetCursor(2, 12);
    	         ssd1306_WriteString(disp_str, Font_7x10, White);
    	         // บรรทัดที่ 3: Duty Cycle (20 - 80%)
    	         sprintf(disp_str, "Duty : %2u %%", duty_val);
    	         ssd1306_SetCursor(2, 24);
    	         ssd1306_WriteString(disp_str, Font_7x10, White);
    	         // บรรทัดที่ 4: ความเร็วรอบ RPM พร้อมทิศทาง [CW] / [CCW] 👈 บรรทัดนี้จะแสดง CW/CCW
    	         sprintf(disp_str, "RPM  : %4u [%s]", (uint16_t)rpm_disp, dir_str);
    	         ssd1306_SetCursor(2, 36);
    	         ssd1306_WriteString(disp_str, Font_7x10, White);
    	         // บรรทัดที่ 5: ค่า Timer Register จริง
    	         sprintf(disp_str, "ARR:%4lu CCR:%4lu", arr_val, ccr_val);
    	         ssd1306_SetCursor(2, 48);
    	         ssd1306_WriteString(disp_str, Font_7x10, White);
    	         // บรรทัดที่ 6: แถบ Progress Bar (0 - 100%)
    	         OLED_DrawBar(2, 58, 124, 6, vr_pct);
    	         ssd1306_UpdateScreen();
    	     }
    	     /* USER CODE END 3 */
      }
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Configure the main internal regulator output voltage
  */
  __HAL_RCC_PWR_CLK_ENABLE();
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
  RCC_OscInitStruct.PLL.PLLM = 16;
  RCC_OscInitStruct.PLL.PLLN = 336;
  RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV4;
  RCC_OscInitStruct.PLL.PLLQ = 4;
  RCC_OscInitStruct.PLL.PLLR = 2;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief ADC1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_ADC1_Init(void)
{

  /* USER CODE BEGIN ADC1_Init 0 */

  /* USER CODE END ADC1_Init 0 */

  ADC_ChannelConfTypeDef sConfig = {0};

  /* USER CODE BEGIN ADC1_Init 1 */

  /* USER CODE END ADC1_Init 1 */

  /** Configure the global features of the ADC (Clock, Resolution, Data Alignment and number of conversion)
  */
  hadc1.Instance = ADC1;
  hadc1.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV4;
  hadc1.Init.Resolution = ADC_RESOLUTION_12B;
  hadc1.Init.ScanConvMode = DISABLE;
  hadc1.Init.ContinuousConvMode = DISABLE;
  hadc1.Init.DiscontinuousConvMode = DISABLE;
  hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
  hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
  hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
  hadc1.Init.NbrOfConversion = 1;
  hadc1.Init.DMAContinuousRequests = DISABLE;
  hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
  if (HAL_ADC_Init(&hadc1) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure for the selected ADC regular channel its corresponding rank in the sequencer and its sample time.
  */
  sConfig.Channel = ADC_CHANNEL_4;
  sConfig.Rank = 1;
  sConfig.SamplingTime = ADC_SAMPLETIME_3CYCLES;
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN ADC1_Init 2 */

  /* USER CODE END ADC1_Init 2 */

}

/**
  * @brief I2C1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_I2C1_Init(void)
{

  /* USER CODE BEGIN I2C1_Init 0 */

  /* USER CODE END I2C1_Init 0 */

  /* USER CODE BEGIN I2C1_Init 1 */

  /* USER CODE END I2C1_Init 1 */
  hi2c1.Instance = I2C1;
  hi2c1.Init.ClockSpeed = 100000;
  hi2c1.Init.DutyCycle = I2C_DUTYCYCLE_2;
  hi2c1.Init.OwnAddress1 = 0;
  hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hi2c1.Init.OwnAddress2 = 0;
  hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
  if (HAL_I2C_Init(&hi2c1) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN I2C1_Init 2 */

  /* USER CODE END I2C1_Init 2 */

}

/**
  * @brief TIM1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM1_Init(void)
{

  /* USER CODE BEGIN TIM1_Init 0 */

  /* USER CODE END TIM1_Init 0 */

  TIM_MasterConfigTypeDef sMasterConfig = {0};
  TIM_OC_InitTypeDef sConfigOC = {0};
  TIM_BreakDeadTimeConfigTypeDef sBreakDeadTimeConfig = {0};

  /* USER CODE BEGIN TIM1_Init 1 */

  /* USER CODE END TIM1_Init 1 */
  htim1.Instance = TIM1;
  htim1.Init.Prescaler = 83;
  htim1.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim1.Init.Period = 999;
  htim1.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim1.Init.RepetitionCounter = 0;
  htim1.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_PWM_Init(&htim1) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim1, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sConfigOC.OCMode = TIM_OCMODE_PWM1;
  sConfigOC.Pulse = 0;
  sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
  sConfigOC.OCNPolarity = TIM_OCNPOLARITY_HIGH;
  sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
  sConfigOC.OCIdleState = TIM_OCIDLESTATE_RESET;
  sConfigOC.OCNIdleState = TIM_OCNIDLESTATE_RESET;
  if (HAL_TIM_PWM_ConfigChannel(&htim1, &sConfigOC, TIM_CHANNEL_1) != HAL_OK)
  {
    Error_Handler();
  }
  sBreakDeadTimeConfig.OffStateRunMode = TIM_OSSR_DISABLE;
  sBreakDeadTimeConfig.OffStateIDLEMode = TIM_OSSI_DISABLE;
  sBreakDeadTimeConfig.LockLevel = TIM_LOCKLEVEL_OFF;
  sBreakDeadTimeConfig.DeadTime = 0;
  sBreakDeadTimeConfig.BreakState = TIM_BREAK_DISABLE;
  sBreakDeadTimeConfig.BreakPolarity = TIM_BREAKPOLARITY_HIGH;
  sBreakDeadTimeConfig.AutomaticOutput = TIM_AUTOMATICOUTPUT_DISABLE;
  if (HAL_TIMEx_ConfigBreakDeadTime(&htim1, &sBreakDeadTimeConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM1_Init 2 */

  /* USER CODE END TIM1_Init 2 */
  HAL_TIM_MspPostInit(&htim1);

}

/**
  * @brief TIM5 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM5_Init(void)
{

  /* USER CODE BEGIN TIM5_Init 0 */

  /* USER CODE END TIM5_Init 0 */

  TIM_Encoder_InitTypeDef sConfig = {0};
  TIM_MasterConfigTypeDef sMasterConfig = {0};

  /* USER CODE BEGIN TIM5_Init 1 */

  /* USER CODE END TIM5_Init 1 */
  htim5.Instance = TIM5;
  htim5.Init.Prescaler = 0;
  htim5.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim5.Init.Period = 4294967295;
  htim5.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim5.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  sConfig.EncoderMode = TIM_ENCODERMODE_TI1;
  sConfig.IC1Polarity = TIM_ICPOLARITY_RISING;
  sConfig.IC1Selection = TIM_ICSELECTION_DIRECTTI;
  sConfig.IC1Prescaler = TIM_ICPSC_DIV1;
  sConfig.IC1Filter = 0;
  sConfig.IC2Polarity = TIM_ICPOLARITY_RISING;
  sConfig.IC2Selection = TIM_ICSELECTION_DIRECTTI;
  sConfig.IC2Prescaler = TIM_ICPSC_DIV1;
  sConfig.IC2Filter = 0;
  if (HAL_TIM_Encoder_Init(&htim5, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim5, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM5_Init 2 */

  /* USER CODE END TIM5_Init 2 */

}

/**
  * @brief USART2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART2_UART_Init(void)
{

  /* USER CODE BEGIN USART2_Init 0 */

  /* USER CODE END USART2_Init 0 */

  /* USER CODE BEGIN USART2_Init 1 */

  /* USER CODE END USART2_Init 1 */
  huart2.Instance = USART2;
  huart2.Init.BaudRate = 115200;
  huart2.Init.WordLength = UART_WORDLENGTH_8B;
  huart2.Init.StopBits = UART_STOPBITS_1;
  huart2.Init.Parity = UART_PARITY_NONE;
  huart2.Init.Mode = UART_MODE_TX_RX;
  huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart2.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart2) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART2_Init 2 */

  /* USER CODE END USART2_Init 2 */

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  /* USER CODE BEGIN MX_GPIO_Init_1 */

  /* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_RESET);

  /*Configure GPIO pin : PC13 */
  GPIO_InitStruct.Pin = GPIO_PIN_13;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

  /*Configure GPIO pin : PA5 */
  GPIO_InitStruct.Pin = GPIO_PIN_5;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

  /* USER CODE BEGIN MX_GPIO_Init_2 */

  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
