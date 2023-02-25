import asyncio, os, openiap, traceback, zlib, json, logging
import random, time
import rpa as r
class Worker:
    async def __ProcessWorkitem(self, workitem, payload):
        logging.info(f"Processing workitem id {workitem._id} retry #{workitem.retries}")
        url = "https://www.google.com"
        if("url" in payload):
            url = payload["url"]
        r.init()
        r.url(url)
        if(url == "https://www.google.com"):
            r.type('//*[@name="q"]', 'decentralisation[enter]')
            # print(r.read('result-stats'))
        r.wait(2)
        r.snap('page', 'results.png')
        r.close()
        payload["url"] = url
        workitem.name = f"loaded {url}"
        return payload
    async def __ProcessWorkitemWrapper(self, workitem):
        try:
            currentfiles = os.listdir(".")
            for f in workitem.files:
                if (f.file and len(f.file) > 0):
                    if f.compressed:
                        with open(f.filename, "wb") as out_file:
                            out_file.write(zlib.decompress(f.file))
                    else:
                        with open(f.filename, "wb") as out_file:
                            out_file.write(f.file)
                else:
                    result = await self.c.DownloadFile(Id=f._id)
            payload = json.loads(workitem.payload)
            payload = await self.__ProcessWorkitem(workitem, payload)
            workitem.payload = json.dumps(payload)
            workitem.state = "successful"
            _files = []
            files = os.listdir(".")
            for file in files:
                if(not file in currentfiles and os.path.isfile(file)):
                    print(f"uploading {file}")
                    _files.append(file)
            await self.c.UpdateWorkitem(workitem, _files, True)
            for file in files:
                if(not file in currentfiles and os.path.isfile(file)):
                    os.unlink(file)
        except (Exception,BaseException) as e:
            workitem.state = "retry"
            workitem.errortype = "application" # business rule will never retry / application will retry as mamy times as defined on the workitem queue
            workitem.errormessage = "".join(traceback.format_exception_only(type(e), e)).strip()
            workitem.errorsource = "".join(traceback.format_exception(e))
            await self.c.UpdateWorkitem(workitem)
            print(repr(e))
            traceback.print_tb(e.__traceback__)
    async def __loop_workitems(self):
        counter = 1
        workitem = await self.c.PopWorkitem(self.wiq)
        while workitem != None:
            counter = counter + 1
            await self.__ProcessWorkitemWrapper(workitem)
            workitem = await self.c.PopWorkitem(self.wiq)
        if(counter > 0):
            logging.info(f"No more workitems in {self.wiq} workitem queue")
    async def __wait_for_message(self, client, message, payload):
        asyncio.run_coroutine_threadsafe(self.__loop_workitems(), client.loop)
        # await self.__loop_workitems()
    async def onconnected(self, client):
        await client.Signin()
        if(self.queue != ""):
            queuename = await self.c.RegisterQueue(self.queue, self.__wait_for_message)
            print(f"Consuming queue {queuename}")
    async def main(self):
        self.queue = os.environ.get("queue", "")
        self.wiq = os.environ.get("wiq", "")
        self.c = openiap.Client()
        self.c.onconnected = self.onconnected
        if(self.queue == ""): self.queue = self.wiq
        if(self.queue == ""):
            await self.c.Signin()
            while True:
                await self.__loop_workitems()
                await asyncio.sleep(30) 
                # time.sleep(30)
        else:
            while True:
                # time.sleep(1)
                await asyncio.sleep(1) 
if __name__ == '__main__':
    loglevel = os.environ.get("loglevel", logging.INFO)
    if loglevel==logging.INFO:
        logging.basicConfig(format="%(message)s", level=loglevel)
    else:
        logging.basicConfig(format="%(levelname)s:%(message)s", level=loglevel)
    wiq = os.environ.get("wiq", "")
    if(wiq == ""): raise ValueError("Workitem queue name (wiq) is required")
    w = Worker()
    asyncio.run(w.main())


