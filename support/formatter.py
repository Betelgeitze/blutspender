class Formatter:

    def dic_to_string(self, rps, termin, language):
        termin_str = str()
        if termin["water"]:
            termin_str = rps[language]["water"]

        clean_termin = {
            rps[language]["date"]: termin["date"],
            rps[language]["city"]: termin["city"],
            rps[language]["street"]: termin["street"],
            rps[language]["building"]: termin["building"],
            rps[language]["times"]: termin["times"],
            rps[language]["link"]: termin["link"]
        }
        for key, value in clean_termin.items():
            if key == rps[language]["times"]:
                value = "\n              ".join(value)
            termin_str += f"{key}: {value}\n"
        return termin_str
