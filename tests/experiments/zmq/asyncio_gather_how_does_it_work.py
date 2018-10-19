import asyncio


async def task1():
    print("Starting task 1!")
    await asyncio.sleep(1)
    print("Done with task 1!")


async def task2():
    print("Starting task 2!")
    await asyncio.sleep(2)
    print("Done with task 2!")


async def task3():
    print("Starting task 3!")
    await asyncio.sleep(3)
    print("Done with task 3!")


async def run_tasks():
    print("Starting all tasks and awaiting finish...")
    await asyncio.gather(task1(), task2(), task3())
    print("-------- Done with tasks! ----------")


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    all_tasks = asyncio.gather(task1(), task2(), task3())

    loop.run_until_complete(all_tasks)

