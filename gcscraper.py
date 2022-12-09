from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from pathlib import Path
from dotenv import load_dotenv
from os import getenv
from time import sleep


class GCScraper:
    def __init__(self, path_to_chromedriver, email, password, downloadDirectory) -> None:
        self.PATH_TO_CHROMEDRIVER = path_to_chromedriver
        self.options = webdriver.ChromeOptions()
        self.prefs = {"download.default_directory": downloadDirectory,
                      'download.directory_upgrade': True}
        self.options.add_experimental_option("prefs", self.prefs)
        self.driver = webdriver.Chrome(
            executable_path=self.PATH_TO_CHROMEDRIVER, options=self.options)
        self.driver.maximize_window()
        self.driver.get("https://www.google.com/")
        self.driver.find_element("name", "q").send_keys(
            "google classroom login")
        self.driver.find_element("name", "q").send_keys(Keys.ENTER)
        self.driver.find_element("partial link text", "Sign in").click()
        self.email = email
        self.password = password
        self.LOGIN_URL = r'https://accounts.google.com/signin/v2/identifier?continue=' + \
            'https%3A%2F%2Fclassroom.google.com&service=classroom&sacu=1&rip=1' + \
            '&flowName=GlifWebSignIn&flowEntry=ServiceLogin'

    def login(self) -> None:
        try:
            self.driver.get(self.LOGIN_URL)
            self.driver.implicitly_wait(15)
            self.driver.find_element(
                "xpath", '//*[@id="identifierId"]').send_keys(self.email)
            self.driver.find_elements(
                "xpath", '//*[@id="identifierNext"]')[0].click()
            self.driver.find_element(
                "xpath", '//*[@id="password"]/div[1]/div/div[1]/input').send_keys(self.password)
            self.driver.find_elements(
                "xpath", '//*[@id="passwordNext"]')[0].click()
            sleep(5)
            self.gcURL = self.driver.current_url
            print("Login Successful")
        except Exception as e:
            print("Login Failed")
            print("Error:", e)

    def getDriver(self) -> webdriver.Chrome:
        return self.driver

    def findCourse(self, courseTitle) -> None:
        try:
            sleep(10)
            course = self.driver.find_element(
                "xpath", f'//div[contains(text(), "{courseTitle}") and @class="YVvGBb z3vRcc-ZoZQ1"]')
            self.courseTitle = course.text
            course.click()
            classwork = self.driver.find_element(
                "xpath", '//a[contains(text(), "Classwork")]')
            classwork.click()
            print("Course Found -", self.courseTitle)
        except Exception as e:
            print("Course Not Found")
            print("Error:", e)

    def getLinks(self) -> list:
        links = []

        self.driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")
        sleep(5)
        viewMore = self.driver.execute_script(
            "return document.getElementsByClassName('VfPpkd-LgbsSe VfPpkd-LgbsSe-OWXEXe-dgl2Hf ksBjEc lKxP2d LQeN7 nZ34k')")

        if viewMore:
            self.driver.execute_script("arguments[0].click()", viewMore[0])
            sleep(2)

            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")
            sleep(5)

        posts = self.driver.execute_script(
            "return document.getElementsByClassName('xVnXCf QRiHXd')")
        print(f"Found {len(posts)} Posts")
        self.driver.implicitly_wait(5)

        for post in posts:
            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);", post)
            self.driver.execute_script("arguments[0].click();", post)

        sleep(5)

        materials = self.driver.execute_script(
            "return document.getElementsByClassName('pOf0gc QRiHXd Aopndd M4LFnf');")
        print(f"Found {len(materials)} Materials")
        self.driver.implicitly_wait(5)

        for material in materials:
            anchors = material.find_elements(By.TAG_NAME, "a")

            for anchor in anchors:
                links.append(anchor.get_attribute("href"))

        return self.courseTitle, links

    def close(self) -> None:
        self.driver.close()


class Downloader:
    def __init__(self, courseTitle, links, driver) -> None:
        self.courseTitle = courseTitle
        self.links = links
        self.driver = driver

    def classifyLinks(self) -> None:
        self.driveLinks = [link for link in self.links if link.split(
            "/")[2] == "drive.google.com"]
        self.otherLinks = [
            link for link in self.links if link not in self.driveLinks]

    def download(self, downloadDirectory) -> None:
        otherLinks = '\n'.join(self.otherLinks)

        directory = Path(downloadDirectory)
        if not directory.exists():
            directory.mkdir(parents=False, exist_ok=False)

        file = Path(f"{downloadDirectory}/{self.courseTitle}.txt")
        file.touch(exist_ok=True)
        file.write_text(otherLinks)
        print("Saved Other Links\n")

        print("Starting Download...\n")
        for link in self.driveLinks:
            print("Downloading:", link)
            self.driver.get(
                f"https://drive.google.com/uc?export=download&id={link.split('/')[5]}")
            sleep(5)
            print("Downloaded\n")


if __name__ == "__main__":
    load_dotenv()

    course_list = list(
        map(lambda x: x[1:-1], getenv("COURSE_LIST")[1:-1].split(", ")))
    path_to_chromedriver = getenv("PATH_TO_CHROMEDRIVER")
    email = getenv("EMAIL")
    password = getenv("PASSWORD")
    downloadDirectory = getenv("DOWNLOAD_DIRECTORY")

    gcscraper = GCScraper(
        path_to_chromedriver=path_to_chromedriver, email=email, password=password, downloadDirectory=downloadDirectory)
    gcscraper.login()
    driver = gcscraper.getDriver()

    for course in course_list:
        gcscraper.findCourse(courseTitle=course)
        ct, links = gcscraper.getLinks()
        downloader = Downloader(courseTitle=ct, links=links, driver=driver)
        downloader.classifyLinks()
        downloader.download(downloadDirectory=downloadDirectory)
        driver.get(gcscraper.gcURL)

    print("Waiting for any remaining downloads to finish...")
    sleep(30)
    print("Done")

    gcscraper.close()
