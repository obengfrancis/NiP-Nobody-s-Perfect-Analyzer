package modules

import (
	"encoding/json"
	"fmt"

	"github.com/gofiber/fiber/v2"
	"github.com/tnp2004/translate-cli/config"
)

type IModule interface {
	Translate(word, target, source string)
}

type module struct {
	config config.IConfig
}

func InitModule(config config.IConfig) IModule {
	return &module{config}
}

type TranslateResponse struct {
	DetectedLanguage struct {
		Language string  `json:"language"`
		Score    float64 `json:"score"`
	} `json:"detectedLanguage"`
	Translations []struct {
		Text string `json:"text"`
		To   string `json:"to"`
	} `json:"translations"`
}

type Translate struct {
	TranslatedText string `json:"Text"`
}

func (m *module) setHeader(agent *fiber.Agent) {
	agent.Set("Content-type", "application/json")
	agent.Set("X-RapidAPI-Key", m.config.App().ApiKey())
	agent.Set("X-RapidAPI-Host", m.config.App().ApiHost())
}

func (m *module) Translate(word, target, source string) {
	endpoint := m.config.App().Url() + fmt.Sprintf("/translate?to%v=%v&api-version=3.0&from=%v&profanityAction=NoAction&textType=plain", "%5B0%5D", target, source)

	payload := []Translate{
		{
			TranslatedText: word,
		},
	}

	payloadByte, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		fmt.Printf("json marshal failed: %v", err)
		return
	}

	agent := fiber.Post(endpoint)
	m.setHeader(agent)
	agent.Body(payloadByte)
	status, body, errs := agent.Bytes()

	if status != 200 {
		fmt.Printf("status code: %v something went wrong", status)
		return
	}

	if len(errs) != 0 {
		for _, e := range errs {
			fmt.Println("Error: ", e)
			return
		}
	}

	translationRes := new([]TranslateResponse)
	if err := json.Unmarshal(body, translationRes); err != nil {
		fmt.Printf("json unmarshal failed: %v", err)
		return
	}

	// Print translation result
	for i, t := range *translationRes {
		fmt.Print("Translation: ")

		// The end of translation result
		if i == len(*translationRes)-1 {
			fmt.Printf("%v\n", t.Translations[i].Text)
			return
		}

		fmt.Printf("%v,", t.Translations[i].Text)
	}
}
